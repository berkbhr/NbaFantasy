import hashlib
import os
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def get_default_db_path():
    primary = os.path.join(DATA_DIR, "processed", "injuries.db")
    os.makedirs(os.path.dirname(primary), exist_ok=True)
    return primary


DB_PATH = get_default_db_path()

# Status codes & play probabilities
STATUS_PROBABILITIES = {
    "HEALTHY": None,  # Uses player's Bayesian availability rate
    "ACTIVE": None,
    "AVAILABLE": None,
    "PROBABLE": 0.90,
    "QUESTIONABLE": 0.52,
    "GTD": 0.52,
    "DTD": 0.52,
    "DOUBTFUL": 0.15,
    "OUT": 0.0,
    "INJ": 0.0,
    "SUSPENDED": 0.0,
    "REST": 0.0,  # When designated as REST for a specific game, play prob is 0.0
    "B2B_REST": 0.05,  # Only applies on the 2nd game of back-to-backs
}


def normalize_name(s):
    if not s:
        return ""
    s_clean = "".join(
        c for c in unicodedata.normalize("NFD", str(s).lower()) if unicodedata.category(c) != "Mn"
    )
    for suffix in (" jr.", " jr", " sr.", " sr", " iii", " ii", " iv"):
        if s_clean.endswith(suffix):
            s_clean = s_clean[: -len(suffix)].strip()
    return s_clean.replace(".", "").replace("'", "").replace("-", " ").strip()


class InjuryTracker:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            # Active status table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS active_injuries (
                    player_id INTEGER PRIMARY KEY,
                    player_name TEXT NOT NULL,
                    norm_name TEXT NOT NULL,
                    team TEXT,
                    status TEXT NOT NULL,
                    injury_desc TEXT,
                    is_b2b_rest INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'manual',
                    expected_return TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_active_norm ON active_injuries(norm_name)")

            # Append-only snapshot history table for backtesting
            cur.execute("""
                CREATE TABLE IF NOT EXISTS injury_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_date TEXT NOT NULL,
                    player_id INTEGER NOT NULL,
                    player_name TEXT NOT NULL,
                    team TEXT,
                    status TEXT NOT NULL,
                    injury_desc TEXT,
                    is_b2b_rest INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'manual',
                    created_at TEXT NOT NULL
                )
            """)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_snap_date ON injury_snapshots(snapshot_date)"
            )
            conn.commit()

    def set_injury(
        self,
        player_id,
        player_name,
        status,
        team=None,
        desc="",
        is_b2b_rest=False,
        source="manual",
        expected_return=None,
    ):
        st_upper = str(status).upper().strip()
        norm_n = normalize_name(player_name)
        now_iso = datetime.now(timezone.utc).isoformat()
        today_date = datetime.now().strftime("%Y-%m-%d")

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO active_injuries (
                    player_id, player_name, norm_name, team, status,
                    injury_desc, is_b2b_rest, source, expected_return, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_id) DO UPDATE SET
                    player_name = excluded.player_name,
                    norm_name = excluded.norm_name,
                    team = COALESCE(excluded.team, team),
                    status = excluded.status,
                    injury_desc = excluded.injury_desc,
                    is_b2b_rest = excluded.is_b2b_rest,
                    source = excluded.source,
                    expected_return = excluded.expected_return,
                    updated_at = excluded.updated_at
            """,
                (
                    player_id,
                    player_name,
                    norm_n,
                    team,
                    st_upper,
                    desc,
                    1 if is_b2b_rest else 0,
                    source,
                    expected_return,
                    now_iso,
                ),
            )

            # Record in snapshot history
            cur.execute(
                """
                INSERT INTO injury_snapshots (
                    snapshot_date, player_id, player_name, team, status,
                    injury_desc, is_b2b_rest, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    today_date,
                    player_id,
                    player_name,
                    team,
                    st_upper,
                    desc,
                    1 if is_b2b_rest else 0,
                    source,
                    now_iso,
                ),
            )
            conn.commit()

    def clear_injury(self, player_id, source="manual"):
        now_iso = datetime.now(timezone.utc).isoformat()
        today_date = datetime.now().strftime("%Y-%m-%d")
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT player_name, team, injury_desc FROM active_injuries WHERE player_id = ?",
                (player_id,),
            )
            row = cur.fetchone()
            if row:
                p_name, team, desc = row[0], row[1], row[2]
                cur.execute(
                    """
                    INSERT INTO injury_snapshots (
                        snapshot_date, player_id, player_name, team, status,
                        injury_desc, is_b2b_rest, source, created_at
                    ) VALUES (?, ?, ?, ?, 'CLEARED', ?, 0, ?, ?)
                """,
                    (
                        today_date,
                        player_id,
                        p_name,
                        team,
                        f"Cleared from active injury list (prev: {desc})",
                        source,
                        now_iso,
                    ),
                )
            cur.execute("DELETE FROM active_injuries WHERE player_id = ?", (player_id,))
            conn.commit()

    def get_injury(self, player_id):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT player_id, player_name, team, status, injury_desc, is_b2b_rest, expected_return, updated_at FROM active_injuries WHERE player_id = ?",
                (player_id,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "player_id": row[0],
                    "player_name": row[1],
                    "team": row[2],
                    "status": row[3],
                    "injury_desc": row[4],
                    "is_b2b_rest": bool(row[5]),
                    "expected_return": row[6],
                    "updated_at": row[7],
                }
            return None

    def get_injury_by_name(self, player_name):
        norm_n = normalize_name(player_name)
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT player_id, player_name, team, status, injury_desc, is_b2b_rest, expected_return, updated_at FROM active_injuries WHERE norm_name = ?",
                (norm_n,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "player_id": row[0],
                    "player_name": row[1],
                    "team": row[2],
                    "status": row[3],
                    "injury_desc": row[4],
                    "is_b2b_rest": bool(row[5]),
                    "expected_return": row[6],
                    "updated_at": row[7],
                }
            return None

    def get_all_active_injuries(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT player_id, player_name, team, status, injury_desc, is_b2b_rest, expected_return, updated_at FROM active_injuries ORDER BY player_name"
            )
            rows = cur.fetchall()
            return [
                {
                    "player_id": r[0],
                    "player_name": r[1],
                    "team": r[2],
                    "status": r[3],
                    "injury_desc": r[4],
                    "is_b2b_rest": bool(r[5]),
                    "expected_return": r[6],
                    "updated_at": r[7],
                }
                for r in rows
            ]

    def get_play_probability(self, player_id, base_avail=0.85, is_b2b=False, player_name=None):
        inj = self.get_injury(player_id)
        if not inj and player_name:
            inj = self.get_injury_by_name(player_name)
        if not inj:
            return base_avail
        st = str(inj.get("status", "HEALTHY")).upper().strip()

        # 1. Definite absences
        if st in ("OUT", "INJ", "SUSPENDED", "REST"):
            return 0.0

        # 2. Back-to-back rest specifically
        if st == "B2B_REST":
            return STATUS_PROBABILITIES["B2B_REST"] if is_b2b else base_avail

        # 3. Known probabilistic statuses (QUESTIONABLE, DOUBTFUL, PROBABLE, etc.)
        prob = STATUS_PROBABILITIES.get(st)
        if prob is not None:
            # If player has is_b2b_rest flag AND it is a B2B, take the stricter probability
            if inj.get("is_b2b_rest") and is_b2b:
                return min(prob, STATUS_PROBABILITIES["B2B_REST"])
            return prob

        # 4. If flag is_b2b_rest is set on an otherwise healthy/active player
        if inj.get("is_b2b_rest") and is_b2b:
            return STATUS_PROBABILITIES["B2B_REST"]

        return base_avail

    def bulk_sync_yahoo_statuses(
        self, status_records, player_resolver_fn, clear_unlisted_teams=None, source="yahoo_sync"
    ):
        """
        Receives records from Yahoo bridge or NBA feed:
        [{'name': 'Kawhi Leonard', 'status': 'OUT', 'desc': 'Knee', 'team': 'TOR'}, ...]
        Resolves to player_id and updates active_injuries.
        If clear_unlisted_teams is provided (set of team strings), players on those teams
        who are no longer reported injured are cleared, tracking return events in snapshots.
        """
        updated = 0
        seen_pids = set()
        for rec in status_records:
            name = rec.get("name")
            if not name:
                continue
            pid = player_resolver_fn(name)
            if pid is None:
                continue
            seen_pids.add(pid)
            status = rec.get("status", "OUT")
            desc = rec.get("desc", "")
            team = rec.get("team", "")
            self.set_injury(
                player_id=pid,
                player_name=name,
                status=status,
                team=team,
                desc=desc,
                source=source,
            )
            updated += 1

        if clear_unlisted_teams:
            all_active = self.get_all_active_injuries()
            for item in all_active:
                if item["team"] in clear_unlisted_teams and item["player_id"] not in seen_pids:
                    self.clear_injury(item["player_id"], source="yahoo_sync_recovery")

        return updated

    def sync_official_report(self, parsed, player_resolver_fn, scraper):
        """Reject unhealthy reports before any injury writes or clearances."""
        try:
            from .nba_injury_scraper import reconcilable_team_codes
        except ImportError:
            from nba_injury_scraper import reconcilable_team_codes
        healthy, rows, _, _ = scraper.run_health_checks(parsed, id_resolver_fn=player_resolver_fn)
        if not healthy:
            return 0
        teams = reconcilable_team_codes(
            {"clean_injuries": rows, "unsubmitted_teams": parsed.get("unsubmitted_teams", [])}
        )
        return self.bulk_sync_yahoo_statuses(
            rows, player_resolver_fn, clear_unlisted_teams=teams, source="official_nba"
        )

    def sync_espn_injuries(self, player_resolver_fn=None, reconcile_recovered=True):
        """
        Fetches official 30-team Rotowire/ESPN injury API (public, zero-credential).
        Captures long-term, multi-week, and off-day injuries that game-day referee reports miss
        (e.g. Maxime Raynaud, Donte DiVincenzo, Mark Williams, Brandon Ingram).
        When `reconcile_recovered=True`, any previously recorded 'espn_rotowire' injury that is no
        longer present in the 30-team feed is automatically cleared (`clear_injury`) so recovered
        teammates' minutes return to them and backup players' temporary minute boosts revert to baseline!
        """
        import requests

        try:
            url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
            resp = requests.get(url, timeout=8.0)
            if resp.status_code != 200:
                return 0
            data = resp.json()
            teams_list = data.get("injuries", [])
            if not teams_list:
                return 0

            updated = 0
            seen_pids = set()
            seen_norm_names = set()
            covered_teams = set()

            for team in teams_list:
                t_name = team.get("displayName", "")
                if t_name and isinstance(team.get("injuries"), list):
                    covered_teams.add(t_name)
                for item in team.get("injuries", []):
                    athlete = item.get("athlete", {})
                    p_name = athlete.get("displayName", "")
                    if not p_name:
                        continue
                    st = item.get("status", "Out")
                    st_lower = st.lower()
                    if "out" in st_lower:
                        st_clean = "OUT"
                    elif "doubt" in st_lower:
                        st_clean = "DOUBTFUL"
                    elif "quest" in st_lower or "day" in st_lower or "gtd" in st_lower:
                        st_clean = "QUESTIONABLE"
                    elif "prob" in st_lower:
                        st_clean = "PROBABLE"
                    else:
                        st_clean = "OUT"

                    desc = (
                        item.get("shortComment", "")
                        or item.get("longComment", "")
                        or item.get("details", {}).get("detail", "")
                    )
                    ret_date = item.get("details", {}).get("returnDate", "")
                    pid = player_resolver_fn(p_name) if player_resolver_fn else None
                    if pid is None:
                        # Fallback: hash the normalized name to a consistent negative integer if not resolved
                        pid = -int(
                            hashlib.sha256(normalize_name(p_name).encode("utf-8")).hexdigest()[:12],
                            16,
                        )

                    seen_pids.add(int(pid))
                    seen_norm_names.add(normalize_name(p_name))

                    self.set_injury(
                        player_id=pid,
                        player_name=p_name,
                        status=st_clean,
                        team=t_name,
                        desc=desc,
                        expected_return=ret_date,
                        source="espn_rotowire",
                    )
                    updated += 1

            # Reconcile only explicitly covered teams. A partial feed must not
            # clear injuries belonging to teams absent from the response.
            if reconcile_recovered and covered_teams:
                with self._get_conn() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT player_id, player_name, source, team FROM active_injuries")
                    existing_rows = cur.fetchall()
                for ex_pid, ex_name, ex_src, ex_team in existing_rows:
                    if ex_team in covered_teams and ex_src == "espn_rotowire":
                        if (
                            int(ex_pid) not in seen_pids
                            and normalize_name(ex_name) not in seen_norm_names
                        ):
                            self.clear_injury(ex_pid, source="espn_recovery_auto")

            return updated
        except Exception:
            return 0
