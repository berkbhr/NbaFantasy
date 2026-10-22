import os
import sqlite3
import unicodedata
import time
from contextlib import contextmanager
from datetime import datetime, timezone
import pandas as pd

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

def get_default_db_path():
    primary = os.path.join(DATA_DIR, 'processed', 'injuries.db')
    os.makedirs(os.path.dirname(primary), exist_ok=True)
    return primary

DB_PATH = get_default_db_path()

# Status codes & play probabilities
STATUS_PROBABILITIES = {
    'HEALTHY': None,          # Uses player's Bayesian availability rate
    'ACTIVE': None,
    'AVAILABLE': None,
    'PROBABLE': 0.90,
    'QUESTIONABLE': 0.52,
    'GTD': 0.52,
    'DTD': 0.52,
    'DOUBTFUL': 0.15,
    'OUT': 0.0,
    'INJ': 0.0,
    'SUSPENDED': 0.0,
    'REST': 0.0,              # When designated as REST for a specific game, play prob is 0.0
    'B2B_REST': 0.05          # Only applies on the 2nd game of back-to-backs
}

def normalize_name(s):
    if not s:
        return ''
    s_clean = ''.join(
        c for c in unicodedata.normalize('NFD', str(s).lower())
        if unicodedata.category(c) != 'Mn'
    )
    for suffix in (' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv'):
        if s_clean.endswith(suffix):
            s_clean = s_clean[:-len(suffix)].strip()
    return s_clean.replace('.', '').replace("'", "").replace('-', ' ').strip()


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
            cur.execute("CREATE INDEX IF NOT EXISTS idx_snap_date ON injury_snapshots(snapshot_date)")
            conn.commit()

    def set_injury(self, player_id, player_name, status, team=None, desc="", is_b2b_rest=False, source="manual", expected_return=None):
        st_upper = str(status).upper().strip()
        norm_n = normalize_name(player_name)
        now_iso = datetime.now(timezone.utc).isoformat()
        today_date = datetime.now().strftime("%Y-%m-%d")

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
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
            """, (player_id, player_name, norm_n, team, st_upper, desc, 1 if is_b2b_rest else 0, source, expected_return, now_iso))

            # Record in snapshot history
            cur.execute("""
                INSERT INTO injury_snapshots (
                    snapshot_date, player_id, player_name, team, status,
                    injury_desc, is_b2b_rest, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (today_date, player_id, player_name, team, st_upper, desc, 1 if is_b2b_rest else 0, source, now_iso))
            conn.commit()

    def clear_injury(self, player_id, source="manual"):
        now_iso = datetime.now(timezone.utc).isoformat()
        today_date = datetime.now().strftime("%Y-%m-%d")
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT player_name, team, injury_desc FROM active_injuries WHERE player_id = ?", (player_id,))
            row = cur.fetchone()
            if row:
                p_name, team, desc = row[0], row[1], row[2]
                cur.execute("""
                    INSERT INTO injury_snapshots (
                        snapshot_date, player_id, player_name, team, status,
                        injury_desc, is_b2b_rest, source, created_at
                    ) VALUES (?, ?, ?, ?, 'CLEARED', ?, 0, ?, ?)
                """, (today_date, player_id, p_name, team, f"Cleared from active injury list (prev: {desc})", source, now_iso))
            cur.execute("DELETE FROM active_injuries WHERE player_id = ?", (player_id,))
            conn.commit()

    def get_injury(self, player_id):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT player_id, player_name, team, status, injury_desc, is_b2b_rest, expected_return, updated_at FROM active_injuries WHERE player_id = ?", (player_id,))
            row = cur.fetchone()
            if row:
                return {
                    'player_id': row[0],
                    'player_name': row[1],
                    'team': row[2],
                    'status': row[3],
                    'injury_desc': row[4],
                    'is_b2b_rest': bool(row[5]),
                    'expected_return': row[6],
                    'updated_at': row[7]
                }
            return None

    def get_all_active_injuries(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT player_id, player_name, team, status, injury_desc, is_b2b_rest, expected_return, updated_at FROM active_injuries ORDER BY player_name")
            rows = cur.fetchall()
            return [
                {
                    'player_id': r[0],
                    'player_name': r[1],
                    'team': r[2],
                    'status': r[3],
                    'injury_desc': r[4],
                    'is_b2b_rest': bool(r[5]),
                    'expected_return': r[6],
                    'updated_at': r[7]
                }
                for r in rows
            ]

    def get_play_probability(self, player_id, base_avail=0.85, is_b2b=False):
        inj = self.get_injury(player_id)
        if not inj:
            return base_avail
        st = str(inj.get('status', 'HEALTHY')).upper().strip()

        # 1. Definite absences
        if st in ('OUT', 'INJ', 'SUSPENDED', 'REST'):
            return 0.0

        # 2. Back-to-back rest specifically
        if st == 'B2B_REST':
            return STATUS_PROBABILITIES['B2B_REST'] if is_b2b else base_avail

        # 3. Known probabilistic statuses (QUESTIONABLE, DOUBTFUL, PROBABLE, etc.)
        prob = STATUS_PROBABILITIES.get(st)
        if prob is not None:
            # If player has is_b2b_rest flag AND it is a B2B, take the stricter probability
            if inj.get('is_b2b_rest') and is_b2b:
                return min(prob, STATUS_PROBABILITIES['B2B_REST'])
            return prob

        # 4. If flag is_b2b_rest is set on an otherwise healthy/active player
        if inj.get('is_b2b_rest') and is_b2b:
            return STATUS_PROBABILITIES['B2B_REST']

        return base_avail

    def bulk_sync_yahoo_statuses(self, status_records, player_resolver_fn, clear_unlisted_teams=None):
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
            name = rec.get('name')
            if not name:
                continue
            pid = player_resolver_fn(name)
            if pid is None:
                continue
            seen_pids.add(pid)
            status = rec.get('status', 'OUT')
            desc = rec.get('desc', '')
            team = rec.get('team', '')
            self.set_injury(
                player_id=pid,
                player_name=name,
                status=status,
                team=team,
                desc=desc,
                source='yahoo_sync'
            )
            updated += 1

        if clear_unlisted_teams:
            all_active = self.get_all_active_injuries()
            for item in all_active:
                if item['team'] in clear_unlisted_teams and item['player_id'] not in seen_pids:
                    self.clear_injury(item['player_id'], source='yahoo_sync_recovery')

        return updated
