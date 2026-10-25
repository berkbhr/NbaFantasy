"""
NBA Fantasy Autonomous Cloud Sync Engine.
Designed to run headless in GitHub Actions or any automated cloud scheduler.

Features:
  1. NBA Official Injury Report Ingestion (Direct from NBA CDN, zero credentials).
  2. Yahoo Fantasy League State Sync (Rosters, IL+ slots, Add/Drops via session cookie if provided).
  3. Real-time Roster Health Audit (Berk's Best Team & League-wide).
  4. Waiver Wire Health Filtering (Excludes Achilles/shoulder/knee long-term injuries).
  5. Live Matchup Projections & IL+ Stashing Recommendations.
  6. Outputs Markdown Report to `reports/latest_cloud_summary.md` and `$GITHUB_STEP_SUMMARY`.
"""
import os
import sys
import zlib
import re
import json
import time
from datetime import datetime, timezone

# Ensure project root and src/ are in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SRC_DIR)

import pandas as pd
from src import draft_data
from src.nba_injury_scraper import (
    NBAOfficialInjuryScraper, parse_report_text, reconcilable_team_codes,
    candidate_report_urls, _default_fetch_bytes
)
from src.injury_tracker import InjuryTracker
from src.live_draft_assistant import LiveDraftAssistant, COUNT_STATS, PERCENTAGE_STATS, norm_cdf
from src.matchup_engine import MatchupEngine
from src.yahoo_draft_sync import YahooFantasyOAuthClient

def extract_pdf_lines_pure(pdf_bytes):
    """Pure-Python zero-dependency extraction of text lines from NBA injury report PDF."""
    streams = list(re.finditer(rb'stream[\r\n]+(.*?)[\r\n]+endstream', pdf_bytes, re.DOTALL))
    all_lines = []
    for m in streams:
        try:
            d = zlib.decompress(m.group(1))
            bts = re.findall(rb'BT[\r\n]+(.*?)[\r\n]+ET', d, re.DOTALL)
            if not bts:
                continue
            tokens = []
            for block in bts:
                cur_x, cur_y = 0.0, 0.0
                for line in block.splitlines():
                    m_td = re.search(rb'(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+Td', line)
                    if m_td:
                        cur_x += float(m_td.group(1))
                        cur_y += float(m_td.group(2))
                    for tj in re.finditer(rb'\((.*?)\)\s*Tj', line):
                        t_str = tj.group(1).decode('latin1', 'ignore').replace(r'\(', '(').replace(r'\)', ')')
                        tokens.append((cur_y, cur_x, t_str))
            # Group by vertical position (5.0pt line tolerance)
            rows_by_y = {}
            for y, x, text in tokens:
                matched_y = None
                for ry in rows_by_y:
                    if abs(ry - y) < 5.0:
                        matched_y = ry
                        break
                if matched_y is None:
                    matched_y = y
                    rows_by_y[matched_y] = []
                rows_by_y[matched_y].append((x, text))
            for y in sorted(rows_by_y):
                sorted_row = sorted(rows_by_y[y], key=lambda item: item[0])
                all_lines.append(' '.join(t for _, t in sorted_row))
        except Exception:
            pass
    return all_lines

def run_cloud_sync():
    now_utc = datetime.now(timezone.utc)
    print("=" * 80)
    print(f"🏀 NBA FANTASY AUTONOMOUS CLOUD SYNC ({now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')})")
    print("=" * 80)

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    db_path = os.path.join(PROCESSED_DIR, "injuries.db")
    tracker = InjuryTracker(db_path=db_path)

    # -------------------------------------------------------------------------
    # STEP 1: OFFICIAL NBA INJURY REPORT INGESTION
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Probing official NBA referee injury reports...")
    scraper = NBAOfficialInjuryScraper()
    raw_pdf_bytes = None
    source_url = None

    for slot, url in candidate_report_urls(now_utc, max_back_steps=48):
        data = _default_fetch_bytes(url, timeout=3.5)
        if data:
            raw_pdf_bytes = data
            source_url = url
            print(f"  Found latest official report: {url}")
            break

    parsed = {'rows': [], 'unsubmitted_teams': [], 'unparsed_lines': []}
    if raw_pdf_bytes:
        # Save rolling buffer (only 1 single file on disk, zero clutter)
        rolling_pdf_path = os.path.join(DATA_DIR, "raw", "injuries", "latest_official_report.pdf")
        os.makedirs(os.path.dirname(rolling_pdf_path), exist_ok=True)
        try:
            with open(rolling_pdf_path, 'wb') as f:
                f.write(raw_pdf_bytes)
        except Exception:
            pass

        # Extract text in-memory
        lines = extract_pdf_lines_pure(raw_pdf_bytes)
        full_text = '\n'.join(lines)
        parsed = parse_report_text(full_text)
        print(f"  Report Time: {parsed.get('report_time_utc')}")
        print(f"  Official Injury Rows Parsed: {len(parsed.get('rows', []))}")
        print(f"  Unsubmitted Teams: {[t['team'] for t in parsed.get('unsubmitted_teams', [])]}")
    else:
        print("  [WARN] No live report PDF found on CDN in recent window. Using cached injuries.db.")

    # -------------------------------------------------------------------------
    # STEP 2: INITIALIZE ASSISTANT & RESOLVE PLAYER IDS
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Initializing assistant & draft rosters...")
    assistant = LiveDraftAssistant(prior_season="2025_26", my_team_idx=draft_data.MY_TEAM_IDX, num_teams=draft_data.NUM_TEAMS)
    rosters = draft_data.resolve_rosters(assistant)
    berk_pids = rosters[draft_data.MY_TEAM_IDX]
    all_drafted_pids = set(p for slot in rosters for p in rosters[slot])

    def resolver(name):
        return assistant.resolve_player_id(name, only_available=False)

    is_healthy, clean_rows, quarantined, metrics = scraper.run_health_checks(
        parsed, games_today_count=None, id_resolver_fn=resolver
    )

    recon_teams = reconcilable_team_codes({'clean_injuries': clean_rows, 'unsubmitted_teams': parsed.get('unsubmitted_teams', [])})
    
    # Sync clean injuries into SQLite database
    updated_db_count = 0
    if clean_rows:
        try:
            updated_db_count = tracker.bulk_sync_yahoo_statuses(clean_rows, resolver, clear_unlisted_teams=recon_teams)
            print(f"  Synchronized {updated_db_count} injuries into SQLite database from referee PDF.")
        except Exception as e:
            print(f"  [WARN] Database sync: {e}")

    # Synchronize all 30 teams from ESPN / Rotowire public API (covers multi-week & off-day injuries)
    try:
        espn_count = tracker.sync_espn_injuries(resolver)
        print(f"  Synchronized {espn_count} league-wide injuries from 30-team ESPN/Rotowire feed.")
    except Exception as e:
        print(f"  [WARN] ESPN injury sync: {e}")

    # Also load all active injuries from DB into assistant.players
    from src.injury_tracker import normalize_name
    active_db = tracker.get_all_active_injuries()
    for item in active_db:
        pid = item['player_id']
        if pid in assistant.players:
            assistant.players[pid].update_injury_status(
                item['status'], desc=item.get('injury_desc', '')
            )
        else:
            norm_target = normalize_name(item['player_name'])
            for p in assistant.players.values():
                if normalize_name(p.name) == norm_target:
                    p.update_injury_status(item['status'], desc=item.get('injury_desc', ''))
                    break

    # Recompute positional depth ranks & teammate injury minute boosts across all 30 NBA teams
    assistant._sync_injuries_into_players()

    # -------------------------------------------------------------------------
    # STEP 3: YAHOO LEAGUE DATA SYNC (OAUTH2 REST API + FALLBACK)
    #   3.1 Live Rosters & IL / IL+ Slots + Empty Active Slots
    #   3.2 Recent Add / Drop / Waiver Transactions
    #   3.3 True Free Agent Pool Reconstruction (Drafted vs Dropped/Added)
    #   3.4 Live Matchup 9-Cat Scoreboard & Remaining Games
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Synchronizing Live Yahoo League State (Rosters, IL+, Transactions, Scoreboard)...")
    yahoo_client = YahooFantasyOAuthClient()
    yahoo_status_msg = "Not configured (using canonical draft rosters)"

    recent_transactions = []
    il_players_by_slot = {slot: [] for slot in rosters}
    unslotted_injured_by_slot = {slot: [] for slot in rosters}
    empty_active_slots_by_slot = {slot: 0 for slot in rosters}
    yahoo_il_eligible_pids = set()

    # Load existing league_state.json if available to preserve previously synced transactions/rosters
    state_json_path = os.path.join(PROCESSED_DIR, "league_state.json")
    prior_state = {}
    if os.path.exists(state_json_path):
        try:
            with open(state_json_path, 'r', encoding='utf-8') as f:
                prior_state = json.load(f)
        except Exception:
            prior_state = {}

    live_rosters_synced = False
    if yahoo_client.client_id and yahoo_client.client_secret and (yahoo_client.refresh_token or yahoo_client.access_token):
        if yahoo_client.discover_league_and_team(target_league_id="64691"):
            roster_payload = yahoo_client.fetch_league_rosters_and_il()
            if roster_payload and roster_payload.get('rosters_by_slot'):
                new_rosters = {}
                for slot_idx, p_list in roster_payload['rosters_by_slot'].items():
                    resolved_pids = []
                    for p_item in p_list:
                        pid = assistant.resolve_player_id(p_item['name'], only_available=False)
                        if pid is not None and pid in assistant.players:
                            resolved_pids.append(pid)
                            if p_item.get('selected_position') in ('IL', 'IL+') or p_item.get('status') in ('IL', 'INJ', 'O', 'OUT'):
                                yahoo_il_eligible_pids.add(pid)
                    if resolved_pids:
                        new_rosters[int(slot_idx)] = resolved_pids
                if len(new_rosters) >= 2:
                    for s_idx, pids_list in new_rosters.items():
                        rosters[s_idx] = pids_list
                    il_players_by_slot = roster_payload.get('il_players_by_slot', il_players_by_slot)
                    unslotted_injured_by_slot = roster_payload.get('unslotted_injured_by_slot', unslotted_injured_by_slot)
                    empty_active_slots_by_slot = roster_payload.get('empty_active_slots_by_slot', empty_active_slots_by_slot)
                    live_rosters_synced = True
                    yahoo_status_msg = f"OAuth2 Live Sync Active (League {yahoo_client.league_key})"
                    print(f"  [OK] {yahoo_status_msg}: Synced {len(new_rosters)} team rosters & IL slots.")
                else:
                    yahoo_status_msg = f"OAuth2 League {yahoo_client.league_key} connected, roster resolution < 2 teams"
            else:
                yahoo_status_msg = f"OAuth2 League {yahoo_client.league_key} connected, roster endpoint: {yahoo_client.last_error or 'empty'}"

            recent_transactions = yahoo_client.fetch_recent_transactions(count=30)
            if recent_transactions:
                print(f"  [OK] Fetched {len(recent_transactions)} recent add/drop transactions.")
                # If full roster endpoint didn't overwrite, apply chronological transactions to rosters
                if not live_rosters_synced:
                    for tx in reversed(recent_transactions):
                        for d_item in tx.get('dropped', []):
                            d_pid = assistant.resolve_player_id(d_item.get('player_name', ''), only_available=False)
                            if d_pid is not None:
                                for s_idx in rosters:
                                    if d_pid in rosters[s_idx]:
                                        rosters[s_idx].remove(d_pid)
                        for a_item in tx.get('added', []):
                            a_pid = assistant.resolve_player_id(a_item.get('player_name', ''), only_available=False)
                            t_name = a_item.get('team_name', '').lower()
                            if a_pid is not None:
                                for s_idx, canonical_tname in enumerate(draft_data.TEAM_NAMES):
                                    if canonical_tname.lower() in t_name or t_name in canonical_tname.lower():
                                        if a_pid not in rosters[s_idx]:
                                            rosters[s_idx].append(a_pid)
                    live_rosters_synced = True
                    yahoo_status_msg = f"OAuth2 Live Transactions Synced (League {yahoo_client.league_key})"

            sb_payload = yahoo_client.fetch_live_scoreboard()
            if sb_payload and sb_payload.get('matchups'):
                print(f"  [OK] Fetched Live Scoreboard for Week {sb_payload.get('week')}.")
                live_rosters_synced = True
                # Locate Berk's matchup
                berk_matchup = None
                for pair in sb_payload['matchups']:
                    names_lower = [p.get('name', '').lower() for p in pair]
                    slots_pair = [p.get('slot', 0) for p in pair]
                    if any('berk' in n for n in names_lower) or (draft_data.MY_TEAM_IDX + 1) in slots_pair:
                        if 'berk' in names_lower[1] or slots_pair[1] == (draft_data.MY_TEAM_IDX + 1):
                            pair = [pair[1], pair[0]]
                        berk_matchup = {
                            "week": sb_payload.get('week', 1),
                            "updated_at": now_utc.isoformat(),
                            "matchup": {
                                "team_a": pair[0],
                                "team_b": pair[1],
                            },
                            "all_matchups": sb_payload['matchups'],
                        }
                        break
                if berk_matchup:
                    live_matchup_path = os.path.join(PROCESSED_DIR, "live_matchup.json")
                    try:
                        with open(live_matchup_path, 'w', encoding='utf-8') as f:
                            json.dump(berk_matchup, f, indent=2)
                    except Exception:
                        pass
        else:
            yahoo_status_msg = f"OAuth2 configured, but league discovery returned False ({yahoo_client.last_error or 'check token/league'})"
            print(f"  [WARN] {yahoo_status_msg}")
    else:
        yahoo_status_msg = "OAuth2 Secret Eksik (GitHub Secrets -> YAHOO_OAUTH_JSON kontrol edin)"
        print("  [INFO] No Yahoo OAuth2 credentials found in config/yahoo_oauth.json or YAHOO_OAUTH_JSON env.")

    # Fallback to Browser Bookmarklet / Bridge synced state in `league_state.json` if OAuth API is pending approval
    if not live_rosters_synced and prior_state.get("rosters"):
        prior_rosters_loaded = 0
        for s_str, name_list in prior_state.get("rosters", {}).items():
            try:
                s_idx = int(s_str)
            except ValueError:
                continue
            resolved_p = []
            for p_name in name_list:
                pid = assistant.resolve_player_id(p_name, only_available=False)
                if pid is not None and pid in assistant.players:
                    resolved_p.append(pid)
            if resolved_p:
                rosters[s_idx] = resolved_p
                prior_rosters_loaded += 1
        if prior_state.get("il_slots"):
            for s_str, il_names in prior_state["il_slots"].items():
                try:
                    il_players_by_slot[int(s_str)] = list(il_names)
                    for il_n in il_names:
                        il_pid = assistant.resolve_player_id(il_n, only_available=False)
                        if il_pid is not None:
                            yahoo_il_eligible_pids.add(il_pid)
                except ValueError:
                    pass
        if prior_state.get("unslotted_injured"):
            for s_str, un_items in prior_state["unslotted_injured"].items():
                try:
                    unslotted_injured_by_slot[int(s_str)] = list(un_items)
                except ValueError:
                    pass
        if prior_state.get("empty_active_slots"):
            for s_str, emp_c in prior_state["empty_active_slots"].items():
                try:
                    empty_active_slots_by_slot[int(s_str)] = int(emp_c)
                except ValueError:
                    pass
        if prior_state.get("live_synced") and prior_rosters_loaded >= 2:
            live_rosters_synced = True
            yahoo_status_msg = prior_state.get("sync_status", "Tarayıcı Köprüsü Aktif (14 Takım Canlı Kadro)")
            print(f"  [OK] Loaded live league state from league_state.json ({yahoo_status_msg}).")

    if not recent_transactions and prior_state.get("transactions"):
        recent_transactions = prior_state.get("transactions", [])

    # Refresh Berk's roster & all_rostered_pids after live roster / transaction updates
    berk_pids = rosters[draft_data.MY_TEAM_IDX]
    all_drafted_pids = set(p for slot in rosters for p in rosters[slot])

    # Identify newly dropped players who are now Free Agents
    initial_draft_rosters = draft_data.resolve_rosters(assistant)
    initial_draft_pids = set(p for slot in initial_draft_rosters for p in initial_draft_rosters[slot])
    dropped_to_fa_pids = [pid for pid in initial_draft_pids if pid not in all_drafted_pids]
    newly_added_from_fa_pids = [pid for pid in all_drafted_pids if pid not in initial_draft_pids]

    league_state = {
        "updated_at": now_utc.isoformat(),
        "league_id": "64691",
        "league_key": yahoo_client.league_key or "nba.l.64691",
        "live_synced": bool(live_rosters_synced),
        "sync_status": yahoo_status_msg,
        "rosters": {str(slot): [assistant.players[p].name for p in pids if p in assistant.players] for slot, pids in rosters.items()},
        "berk_roster_names": [assistant.players[p].name for p in berk_pids if p in assistant.players],
        "il_slots": {str(slot): names for slot, names in il_players_by_slot.items()},
        "unslotted_injured": {str(slot): items for slot, items in unslotted_injured_by_slot.items()},
        "empty_active_slots": {str(slot): cnt for slot, cnt in empty_active_slots_by_slot.items()},
        "transactions": recent_transactions[:25],
        "dropped_free_agents": [assistant.players[p].name for p in dropped_to_fa_pids if p in assistant.players],
        "added_streamers": [assistant.players[p].name for p in newly_added_from_fa_pids if p in assistant.players],
    }

    # Save state JSON
    try:
        with open(state_json_path, 'w', encoding='utf-8') as f:
            json.dump(league_state, f, indent=2)
    except Exception:
        pass

    # -------------------------------------------------------------------------
    # STEP 4: BERK'S TEAM & LEAGUE-WIDE IL / SLOT AUDIT
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Auditing Berk's Best Team health & IL/Slot status...")
    roster_health = []
    stashed_il_candidates = []
    berk_il_names = set(il_players_by_slot.get(draft_data.MY_TEAM_IDX, []))
    for pid in berk_pids:
        p = assistant.players[pid]
        eff_avail = p.get_effective_game_availability(is_b2b=False)
        inj_status = getattr(p, 'injury_status', 'HEALTHY')
        inj_desc = getattr(p, 'injury_desc', '')
        is_out = eff_avail <= 0.0 or inj_status in ('OUT', 'INJ', 'SUSPENDED')
        in_yahoo_il = p.name in berk_il_names
        if is_out:
            stashed_il_candidates.append(pid)
        slot_badge = "IL+" if in_yahoo_il else ("⚠️ Move to IL+" if is_out else "Active/BN")
        roster_health.append({
            'pid': pid,
            'name': p.name,
            'status': inj_status,
            'slot_state': slot_badge,
            'eff_avail': eff_avail,
            'desc': inj_desc,
            'is_out': is_out
        })
        status_tag = "❌ OUT" if is_out else ("⚠️ " + inj_status if eff_avail < 0.85 else "✅ Healthy")
        print(f"  {p.name:22s} | Slot: {slot_badge:14s} | Status: {status_tag:12s} | Avail: {eff_avail:.2f}")

    # -------------------------------------------------------------------------
    # STEP 5: TRUE FREE AGENT POOL RECONSTRUCTION & HEALTH FILTERING
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Reconstructing True Free Agent & Waiver Wire Pool...")
    # All players in assistant.df_base who are NOT currently on any of the 14 live rosters
    all_candidate_fa_pids = [
        pid for pid in assistant.df_base.index
        if pid not in all_drafted_pids and pid in assistant.players
    ]
    avail_df = assistant.df_base.loc[all_candidate_fa_pids]
    ranked_fa_pids = list(avail_df.sort_values('BASE_Z', ascending=False).index)

    healthy_free_agents = []
    injured_free_agents = []
    for pid in ranked_fa_pids:
        p = assistant.players[pid]
        eff_avail = p.get_effective_game_availability(is_b2b=False)
        inj_status = getattr(p, 'injury_status', 'HEALTHY')
        z_val = float(assistant.df_base.loc[pid, 'BASE_Z'])
        is_injured = eff_avail <= 0.80 or inj_status in ('OUT', 'INJ', 'SUSPENDED', 'DOUBTFUL')
        was_dropped = pid in dropped_to_fa_pids
        if not is_injured:
            healthy_free_agents.append((pid, p.name, z_val, eff_avail, was_dropped))
        else:
            injured_free_agents.append((pid, p.name, z_val, eff_avail, getattr(p, 'injury_desc', 'Injured/Out')))
        if len(healthy_free_agents) >= 25:
            break

    print(f"  Top 3 HEALTHY Free Agents: {[x[1] for x in healthy_free_agents[:3]]}")
    print(f"  Filtered OUT Injured FAs: {[x[1] for x in injured_free_agents[:3]]}")

    # -------------------------------------------------------------------------
    # STEP 6: LIVE MATCHUP SCOREBOARD, REMAINING SCHEDULE & ADD/DROP ENGINE
    # -------------------------------------------------------------------------
    print("\n[STEP 6] Running Live Matchup Engine & Remaining-Games Add/Drop Optimizer...")
    # Load NBA schedule if available for exact remaining games calculation
    sched_df = pd.DataFrame()
    for sched_cand in ("schedule_2025_26.parquet", "schedule_2024_25.parquet"):
        sp = os.path.join(DATA_DIR, "raw", sched_cand)
        if os.path.exists(sp):
            try:
                sched_df = pd.read_parquet(sp)
                break
            except Exception:
                pass

    top_fa_ids = [item[0] for item in healthy_free_agents]
    engine = MatchupEngine(
        bayesian_players_dict=assistant.players,
        df_schedule=sched_df,
        df_positions=assistant.df_pos,
        season=assistant.target_season,
        prior_season=assistant.prior_season,
        free_agent_pool=top_fa_ids[:10],
        num_il_slots=2,
        max_weekly_adds=3,
        yahoo_il_eligible_ids=yahoo_il_eligible_pids if yahoo_il_eligible_pids else None,
        use_dynamic_add_drop=True,
        use_positional_depth_and_injury_boost=True
    )

    # Check for live in-week matchup state (data/processed/live_matchup.json)
    # Schema Guard: Reject partial/stale mock files that have games_played > 0 but are missing core counting stats
    live_matchup_file = os.path.join(PROCESSED_DIR, "live_matchup.json")
    live_data = None
    if os.path.exists(live_matchup_file):
        try:
            with open(live_matchup_file, 'r', encoding='utf-8') as f:
                cand_matchup = json.load(f).get('matchup', {})
            ta_cand = cand_matchup.get('team_a', {})
            tb_cand = cand_matchup.get('team_b', {})
            required_live_keys = ('PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'TOV', 'FGM', 'FGA', 'FTM', 'FTA')
            has_all_cats = all(k in ta_cand and k in tb_cand for k in required_live_keys)
            is_zero_games = int(ta_cand.get('games_played', 0)) == 0 and int(tb_cand.get('games_played', 0)) == 0
            if cand_matchup and (has_all_cats or is_zero_games):
                live_data = cand_matchup
            else:
                print("  [WARN] Ignored incomplete/stale live_matchup.json (missing 9-cat stats for played games).")
        except Exception:
            pass

    # Determine opponent slot from live_data or default to Slot 13 (SILE BULLS, index 12)
    opp_slot_idx = 12
    opp_team_name = "SILE BULLS"
    if live_data and live_data.get('team_b'):
        tb_slot = int(live_data['team_b'].get('slot', 13)) - 1
        if 0 <= tb_slot < draft_data.NUM_TEAMS:
            opp_slot_idx = tb_slot
        opp_team_name = live_data['team_b'].get('name', opp_team_name)

    opp_pids = rosters.get(opp_slot_idx, rosters[12])
    dist_berk = engine.get_expected_weekly_distribution(berk_pids)
    dist_sile = engine.get_expected_weekly_distribution(opp_pids)

    fa = 1.0
    fb = 1.0
    ta = {}
    tb = {}
    table_rows = []
    if live_data:
        ta = live_data.get('team_a', {})
        tb = live_data.get('team_b', {})
        fa = ta.get('games_remaining', 26) / max(ta.get('total_scheduled', 37), 1)
        fb = tb.get('games_remaining', 24) / max(tb.get('total_scheduled', 36), 1)

        comb_berk = MatchupEngine.combine_live_and_remaining_dist(ta, dist_berk, rem_fraction=fa)
        comb_opp = MatchupEngine.combine_live_and_remaining_dist(tb, dist_sile, rem_fraction=fb)
        exp_score, live_win_probs, _ = MatchupEngine.evaluate_h2h_matchup(comb_berk, comb_opp)
        active_win_probs = live_win_probs
        matchup_win_prob = MatchupEngine.compute_matchup_win_prob(active_win_probs)

        for cat in COUNT_STATS:
            mu_a = comb_berk['mean'][cat]
            mu_b = comb_opp['mean'][cat]
            p = live_win_probs[cat]
            winner = "🏆 Berk" if p > 0.52 else (opp_team_name if p < 0.48 else "⚖️ Toss-up")
            curr_str = f"{int(ta.get(cat, 0))} - {int(tb.get(cat, 0))}"
            table_rows.append(f"| **{cat}** | `{curr_str}` | `{mu_a:.1f}` | `{mu_b:.1f}` | `%{p*100:.1f}` | {winner} |")

        # FG%
        fgm_a, fga_a = comb_berk['mean']['FGM'], max(comb_berk['mean']['FGA'], 1.0)
        fgm_b, fga_b = comb_opp['mean']['FGM'], max(comb_opp['mean']['FGA'], 1.0)
        fg_pct_a, fg_pct_b = fgm_a / fga_a, fgm_b / fga_b
        p_fg = live_win_probs['FG_PCT']
        curr_fg_a = ta.get('FGM', 0) / max(ta.get('FGA', 1), 1) if ta.get('FGA', 0) > 0 else fg_pct_a
        curr_fg_b = tb.get('FGM', 0) / max(tb.get('FGA', 1), 1) if tb.get('FGA', 0) > 0 else fg_pct_b
        curr_fg = f".{int(round(curr_fg_a*1000)):03d} - .{int(round(curr_fg_b*1000)):03d}"
        winner_fg = "🏆 Berk" if p_fg > 0.5 else opp_team_name
        table_rows.append(f"| **FG%** | `{curr_fg}` | `.{int(round(fg_pct_a*1000)):03d}` | `.{int(round(fg_pct_b*1000)):03d}` | `%{p_fg*100:.1f}` | {winner_fg} |")

        # FT%
        ftm_a, fta_a = comb_berk['mean']['FTM'], max(comb_berk['mean']['FTA'], 1.0)
        ftm_b, fta_b = comb_opp['mean']['FTM'], max(comb_opp['mean']['FTA'], 1.0)
        ft_pct_a, ft_pct_b = ftm_a / fta_a, ftm_b / fta_b
        p_ft = live_win_probs['FT_PCT']
        curr_ft_a = ta.get('FTM', 0) / max(ta.get('FTA', 1), 1) if ta.get('FTA', 0) > 0 else ft_pct_a
        curr_ft_b = tb.get('FTM', 0) / max(tb.get('FTA', 1), 1) if tb.get('FTA', 0) > 0 else ft_pct_b
        curr_ft = f".{int(round(curr_ft_a*1000)):03d} - .{int(round(curr_ft_b*1000)):03d}"
        winner_ft = "🏆 Berk" if p_ft > 0.5 else opp_team_name
        table_rows.append(f"| **FT%** | `{curr_ft}` | `.{int(round(ft_pct_a*1000)):03d}` | `.{int(round(ft_pct_b*1000)):03d}` | `%{p_ft*100:.1f}` | {winner_ft} |")

        header_table = f"| Category | Live Score | Berk Proj Final | {opp_team_name} Proj Final | Berk Win Prob | Projected Winner |\n| :--- | :---: | :---: | :---: | :---: | :---: |"
    else:
        comb_berk = dist_berk
        comb_opp = dist_sile
        exp_score, win_probs, _ = MatchupEngine.evaluate_h2h_matchup(dist_berk, dist_sile)
        active_win_probs = win_probs
        matchup_win_prob = MatchupEngine.compute_matchup_win_prob(active_win_probs)
        fg_b = dist_berk['mean']['FGM'] / dist_berk['mean']['FGA']
        fg_s = dist_sile['mean']['FGM'] / dist_sile['mean']['FGA']
        ft_b = dist_berk['mean']['FTM'] / dist_berk['mean']['FTA']
        ft_s = dist_sile['mean']['FTM'] / dist_sile['mean']['FTA']
        for cat in COUNT_STATS:
            m_b = dist_berk['mean'][cat]
            m_s = dist_sile['mean'][cat]
            wp = win_probs.get(cat, 0.5)
            winner = "🏆 Berk" if wp > 0.52 else (opp_team_name if wp < 0.48 else "⚖️ Toss-up")
            table_rows.append(f"| **{cat}** | `{m_b:.1f}` | `{m_s:.1f}` | `%{wp*100:.1f}` | {winner} |")
        wp_fg = win_probs.get('FG_PCT', 0.5)
        wp_ft = win_probs.get('FT_PCT', 0.5)
        table_rows.append(f"| **FG%** | `.{int(round(fg_b*1000)):03d}` | `.{int(round(fg_s*1000)):03d}` | `%{wp_fg*100:.1f}` | {'🏆 Berk' if wp_fg > 0.5 else opp_team_name} |")
        table_rows.append(f"| **FT%** | `.{int(round(ft_b*1000)):03d}` | `.{int(round(ft_s*1000)):03d}` | `%{wp_ft*100:.1f}` | {'🏆 Berk' if wp_ft > 0.5 else opp_team_name} |")
        header_table = f"| Category | Berk's Expected | {opp_team_name} Expected | Berk Win Prob | Projected Winner |\n| :--- | :---: | :---: | :---: | :---: |"

    # Compute Remaining-Games Marginal Add/Drop Recommendations
    add_drop_recs = engine.recommend_add_drop_moves(
        my_roster_ids=berk_pids,
        opp_roster_ids=opp_pids,
        candidate_fa_ids=top_fa_ids,
        my_actual_stats=ta if live_data else None,
        opp_actual_stats=tb if live_data else None,
        my_rem_fraction=fa,
        opp_rem_fraction=fb,
        top_k=5
    )

    print(f"  Berk IL+ Stashed: {[assistant.players[p].name for p in dist_berk.get('meta', {}).get('il_stashed_ids', [])]}")
    print(f"  Berk Streamer Added: {[assistant.players[p].name for p in dist_berk.get('meta', {}).get('streamer_ids', [])]}")
    print(f"  Expected Score vs {opp_team_name}: {exp_score:.2f} - {9.0 - exp_score:.2f}")
    if add_drop_recs:
        top_move = add_drop_recs[0]
        print(f"  Top Marginal Add/Drop Move: {top_move['action']} -> +{top_move['add_name']} (Drop: {top_move['drop_name']}) | Delta E[Wins]: {top_move['delta_expected_wins']:+.3f}")

    # -------------------------------------------------------------------------
    # STEP 7: BUILD COMPREHENSIVE MARKDOWN SUMMARY REPORT
    # -------------------------------------------------------------------------
    report_lines = [
        "# 🏀 NBA Fantasy Autonomous Cloud Sync Report",
        f"**Sync Timestamp:** `{now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}`  ",
        f"**Official NBA Ingestion:** `{source_url if source_url else 'Using cached/prior report'}`  ",
        f"**Yahoo League Status:** `{yahoo_status_msg}`  ",
        "",
        "---",
        "",
        "## 1. 🛡️ Berk's Best Team Roster, IL+ & Slot Audit",
        "| Player | Active/IL+ Slot | Status | Play Probability | Notes / Reason |",
        "| :--- | :---: | :---: | :---: | :--- |"
    ]

    for item in roster_health:
        tag = "**OUT**" if item['is_out'] else (f"**{item['status']}**" if item['eff_avail'] < 0.85 else "Healthy")
        icon = "❌" if item['is_out'] else ("⚠️" if item['eff_avail'] < 0.85 else "✅")
        desc_str = item['desc'] if item['desc'] else "Expected to play"
        report_lines.append(f"| {icon} **{item['name']}** | `{item['slot_state']}` | {tag} | `{item['eff_avail']:.2f}` | {desc_str} |")

    # League-wide IL+ & Empty Slot Summary
    report_lines.extend([
        "",
        "### 🔍 League-Wide IL+ Stashes & Open Roster Slots",
        "| Slot & Team | Players in IL/IL+ | Injured in Active/BN (Needs IL) | Empty Active Roster Spots |",
        "| :--- | :--- | :--- | :---: |"
    ])
    for s_idx in range(draft_data.NUM_TEAMS):
        t_label = f"#{s_idx+1} {draft_data.TEAM_NAMES[s_idx]}"
        il_names = il_players_by_slot.get(s_idx, [])
        unslotted = [f"{x['name']} ({x['status']})" for x in unslotted_injured_by_slot.get(s_idx, [])]
        # Fallback if OAuth wasn't connected: infer from roster injury statuses
        if not il_names and not unslotted:
            for p_id in rosters.get(s_idx, []):
                if p_id in assistant.players:
                    bp = assistant.players[p_id]
                    st_str = getattr(bp, 'injury_status', 'HEALTHY')
                    if bp.get_effective_game_availability(is_b2b=False) <= 0.0 or st_str in ('OUT', 'INJ'):
                        unslotted.append(f"{bp.name} ({st_str})")
        emp_cnt = empty_active_slots_by_slot.get(s_idx, max(0, 13 - len(rosters.get(s_idx, []))))
        if il_names or unslotted or emp_cnt > 0 or s_idx == draft_data.MY_TEAM_IDX:
            report_lines.append(
                f"| **{t_label}** | {', '.join(il_names) if il_names else '—'} | {', '.join(unslotted) if unslotted else '—'} | `{emp_cnt}` |"
            )

    # Recent League Add/Drop Transactions Section
    report_lines.extend([
        "",
        "---",
        "",
        "## 2. 🔄 Recent League Transactions (Who Added / Dropped Whom)",
    ])
    if recent_transactions:
        report_lines.extend([
            "| Transaction | Team | Added Player(s) | Dropped Player(s) |",
            "| :---: | :--- | :--- | :--- |"
        ])
        for tx in recent_transactions[:12]:
            adds_str = ", ".join([f"➕ **{a['player_name']}**" for a in tx.get('added', [])]) or "—"
            drops_str = ", ".join([f"➖ {d['player_name']}" for d in tx.get('dropped', [])]) or "—"
            t_name = (
                tx['added'][0]['team_name'] if tx.get('added')
                else (tx['dropped'][0]['team_name'] if tx.get('dropped') else "League")
            )
            report_lines.append(f"| `{tx.get('type', 'add/drop').upper()}` | **{t_name}** | {adds_str} | {drops_str} |")
    else:
        dropped_names = league_state.get("dropped_free_agents", [])
        added_names = league_state.get("added_streamers", [])
        if dropped_names or added_names:
            report_lines.append(f"* **Recently Added to Rosters:** {', '.join(added_names) if added_names else 'None'}")
            report_lines.append(f"* **Recently Dropped to Waivers:** {', '.join(dropped_names) if dropped_names else 'None'}")
        else:
            report_lines.append("* *No live transactions recorded yet (or awaiting Yahoo OAuth token refresh).*")

    # Dynamic Add/Drop Recommendations & Free Agent Pool
    report_lines.extend([
        "",
        "---",
        "",
        "## 3. 🎯 Dynamic Add/Drop Recommendations (Remaining Games & Live Scoreboard Weighted)",
        "Optimized via $\\Delta \\sum_{c=1}^{9} \\Phi_c$ conditioned on live category margins and remaining games this week:",
        "",
        "| Rank | Action | Add Target (FA) | Drop Candidate | Rem Games (Add/Drop) | $\\Delta E[\\text{Wins}]$ | Key Category Gains |",
        "| :---: | :---: | :--- | :--- | :---: | :---: | :--- |"
    ])
    for idx_r, rec in enumerate(add_drop_recs, 1):
        rg_str = f"{rec['rem_games_add']:.1f} / {rec['rem_games_drop']:.1f}"
        report_lines.append(
            f"| #{idx_r} | `{rec['action']}` | **{rec['add_name']}** | {rec['drop_name']} | `{rg_str}` | **`{rec['delta_expected_wins']:+.3f}`** | {rec['key_cat_gains']} |"
        )

    report_lines.extend([
        "",
        "### 📋 Available Healthy Free Agents Pool (Top 8)",
        "| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |",
        "| :---: | :--- | :---: | :---: | :---: | :---: |"
    ])
    for i, (pid, name, z_val, eff_avail, was_dropped) in enumerate(healthy_free_agents[:8], 1):
        src_tag = "🔥 Dropped by Team" if was_dropped else "Unrostered FA"
        bp_fa = assistant.players[pid]
        base_m_fa = getattr(bp_fa, 'base_expected_minutes', bp_fa.expected_minutes)
        boost_fa = bp_fa.expected_minutes - base_m_fa
        min_str = f"{bp_fa.expected_minutes:.1f}m ({boost_fa:+.1f}m)" if abs(boost_fa) >= 0.5 else f"{bp_fa.expected_minutes:.1f}m"
        report_lines.append(f"| #{i} | **{name}** | `{src_tag}` | `{min_str}` | `{z_val:.2f}` | `{eff_avail:.2f}` |")

    report_lines.extend([
        "",
        "---",
        "",
        f"## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs {opp_team_name}",
        f"* **IL+ Stash:** `{', '.join([assistant.players[p].name for p in dist_berk.get('meta', {}).get('il_stashed_ids', [])]) if dist_berk.get('meta', {}).get('il_stashed_ids') else 'None'}`",
        f"* **Top Auto-Streamer:** `{', '.join([assistant.players[p].name for p in dist_berk.get('meta', {}).get('streamer_ids', [])]) if dist_berk.get('meta', {}).get('streamer_ids') else 'None'}`",
        f"* **Remaining Games Multiplier:** `Berk: {fa*100:.0f}% remaining | {opp_team_name}: {fb*100:.0f}% remaining`",
        f"* **Expected Matchup Outcome:** **{exp_score:.2f} - {9.0 - exp_score:.2f}** | **Matchup Win Prob $P(\\ge 5\\text{{ cats}})$:** **`%{matchup_win_prob*100:.1f}`** ({'Berk favori' if exp_score >= 4.5 else opp_team_name + ' favori'})",
        "",
        header_table
    ])
    report_lines.extend(table_rows)

    full_markdown = '\n'.join(report_lines)
    summary_path = os.path.join(REPORTS_DIR, "latest_cloud_summary.md")
    try:
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(full_markdown)
        print(f"\n[STEP 7] Saved executive report to {summary_path}")
    except Exception as e:
        print(f"  [WARN] Could not write report: {e}")

    # Output to GitHub Step Summary if running in GitHub Actions
    gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh_summary:
        try:
            with open(gh_summary, 'a', encoding='utf-8') as f:
                f.write(full_markdown)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # STEP 8: COMPREHENSIVE MULTI-CHANNEL NOTIFICATION ENGINE (TELEGRAM + DISCORD)
    # -------------------------------------------------------------------------
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not (tg_token and tg_chat):
        tg_conf_path = os.path.join(PROJECT_ROOT, "config", "telegram.json")
        if os.path.exists(tg_conf_path):
            try:
                with open(tg_conf_path, 'r', encoding='utf-8') as f:
                    tg_conf = json.load(f)
                    tg_token = tg_token or str(tg_conf.get("bot_token", "")).strip()
                    tg_chat = tg_chat or str(tg_conf.get("chat_id", "")).strip()
                    discord_webhook = discord_webhook or str(tg_conf.get("discord_webhook_url", "")).strip()
            except Exception:
                pass

    # Build Clean, Mobile-Friendly Executive Notification Card (Telegram HTML & Discord Markdown)
    out_items = [item for item in roster_health if item['is_out']]
    gtd_items = [item for item in roster_health if not item['is_out'] and item['eff_avail'] < 0.80]

    # Category breakdown strings (clean dot-separated pills)
    strong_cats, tossup_cats, weak_cats = [], [], []
    for c_key, p_val in active_win_probs.items():
        c_lbl = c_key.replace('_PCT', '%').replace('FG3M', '3PT')
        if p_val >= 0.58:
            strong_cats.append(f"{c_lbl} (%{p_val*100:.0f})")
        elif p_val <= 0.42:
            weak_cats.append(f"{c_lbl} (%{p_val*100:.0f})")
        else:
            tossup_cats.append(f"{c_lbl} (%{p_val*100:.0f})")

    sync_badge = (
        f"🟢 Canlı Yahoo Senkron Aktif ({yahoo_client.league_key or '64691'})"
        if live_rosters_synced
        else f"🟡 Yedek Kadro Modu ({yahoo_status_msg[:48]})"
    )
    gp_a = int(ta.get('games_played', 0)) if live_data else 0
    rem_a = int(ta.get('games_remaining', 37)) if live_data else 37
    tot_a = int(ta.get('total_scheduled', max(gp_a + rem_a, 37))) if live_data else 37
    gp_b = int(tb.get('games_played', 0)) if live_data else 0
    rem_b = int(tb.get('games_remaining', 36)) if live_data else 36
    tot_b = int(tb.get('total_scheduled', max(gp_b + rem_b, 36))) if live_data else 36

    # Build Yahoo-style Comparative Box Score Table (Live + Projected Final) for BOTH teams
    opp_short = opp_team_name[:10].upper()
    box_lines = []
    if live_data and (gp_a > 0 or gp_b > 0):
        fgm_la, fga_la = int(round(ta.get('FGM', 0))), int(round(ta.get('FGA', 0)))
        fgm_lb, fga_lb = int(round(tb.get('FGM', 0))), int(round(tb.get('FGA', 0)))
        fgp_la = fgm_la / max(fga_la, 1) if fga_la > 0 else 0.0
        fgp_lb = fgm_lb / max(fga_lb, 1) if fga_lb > 0 else 0.0

        ftm_la, fta_la = int(round(ta.get('FTM', 0))), int(round(ta.get('FTA', 0)))
        ftm_lb, fta_lb = int(round(tb.get('FTM', 0))), int(round(tb.get('FTA', 0)))
        ftp_la = ftm_la / max(fta_la, 1) if fta_la > 0 else 0.0
        ftp_lb = ftm_lb / max(fta_lb, 1) if fta_lb > 0 else 0.0

        live_wins_a, live_wins_b = 0, 0
        def _win_tag(va, vb, lower_better=False):
            nonlocal live_wins_a, live_wins_b
            if abs(va - vb) < 1e-6:
                return "⚖️Ber"
            is_a = (va < vb) if lower_better else (va > vb)
            if is_a:
                live_wins_a += 1
                return "🟢Berk"
            else:
                live_wins_b += 1
                return "🔴Rakip"

        live_rows = [
            ("FGM/A", f"{fgm_la}/{fga_la}", f"{fgm_lb}/{fga_lb}", "  —"),
            ("FG%",   f".{int(round(fgp_la*1000)):03d}", f".{int(round(fgp_lb*1000)):03d}", _win_tag(fgp_la, fgp_lb)),
            ("FTM/A", f"{ftm_la}/{fta_la}", f"{ftm_lb}/{fta_lb}", "  —"),
            ("FT%",   f".{int(round(ftp_la*1000)):03d}", f".{int(round(ftp_lb*1000)):03d}", _win_tag(ftp_la, ftp_lb)),
            ("3PTM",  f"{int(round(ta.get('FG3M', 0)))}", f"{int(round(tb.get('FG3M', 0)))}", _win_tag(ta.get('FG3M', 0), tb.get('FG3M', 0))),
            ("PTS",   f"{int(round(ta.get('PTS', 0)))}",  f"{int(round(tb.get('PTS', 0)))}",  _win_tag(ta.get('PTS', 0), tb.get('PTS', 0))),
            ("REB",   f"{int(round(ta.get('REB', 0)))}",  f"{int(round(tb.get('REB', 0)))}",  _win_tag(ta.get('REB', 0), tb.get('REB', 0))),
            ("AST",   f"{int(round(ta.get('AST', 0)))}",  f"{int(round(tb.get('AST', 0)))}",  _win_tag(ta.get('AST', 0), tb.get('AST', 0))),
            ("ST",    f"{int(round(ta.get('STL', 0)))}",  f"{int(round(tb.get('STL', 0)))}",  _win_tag(ta.get('STL', 0), tb.get('STL', 0))),
            ("BLK",   f"{int(round(ta.get('BLK', 0)))}",  f"{int(round(tb.get('BLK', 0)))}",  _win_tag(ta.get('BLK', 0), tb.get('BLK', 0))),
            ("TO",    f"{int(round(ta.get('TOV', 0)))}",  f"{int(round(tb.get('TOV', 0)))}",  _win_tag(ta.get('TOV', 0), tb.get('TOV', 0), lower_better=True)),
        ]
        box_lines.append("📋 <b>ANLIK YAHOO SKOR TABLOSU (Canlı)</b>")
        pre_live = [
            f"{'KAT':<5} {'BERK':>9} {opp_short:>10}  {'LİDER':<6}",
            "─" * 34,
        ]
        for c_name, v_a, v_b, w_t in live_rows:
            pre_live.append(f"{c_name:<5} {v_a:>9} {v_b:>10}  {w_t}")
        pre_live.append("─" * 34)
        pre_live.append(f"SKOR: Berk {live_wins_a} - {live_wins_b} {opp_team_name[:12]}")
        box_lines.append("<pre>" + "\n".join(pre_live) + "</pre>")

    # Projected End-of-Week Final Table (Live + Remaining Games Combined)
    p_fgm_a, p_fga_a = comb_berk['mean']['FGM'], max(comb_berk['mean']['FGA'], 1.0)
    p_fgm_b, p_fga_b = comb_opp['mean']['FGM'], max(comb_opp['mean']['FGA'], 1.0)
    p_fg_a, p_fg_b = p_fgm_a / p_fga_a, p_fgm_b / p_fga_b

    p_ftm_a, p_fta_a = comb_berk['mean']['FTM'], max(comb_berk['mean']['FTA'], 1.0)
    p_ftm_b, p_fta_b = comb_opp['mean']['FTM'], max(comb_opp['mean']['FTA'], 1.0)
    p_ft_a, p_ft_b = p_ftm_a / p_fta_a, p_ftm_b / p_fta_b

    def _prob_tag(cat_key):
        wp_v = active_win_probs.get(cat_key, 0.5)
        ico = "🟢" if wp_v >= 0.52 else ("🔴" if wp_v <= 0.48 else "⚖️")
        return f"%{wp_v*100:2.0f}{ico}"

    proj_rows = [
        ("FGM/A", f"{int(round(p_fgm_a))}/{int(round(p_fga_a))}", f"{int(round(p_fgm_b))}/{int(round(p_fga_b))}", "  —"),
        ("FG%",   f".{int(round(p_fg_a*1000)):03d}", f".{int(round(p_fg_b*1000)):03d}", _prob_tag('FG_PCT')),
        ("FTM/A", f"{int(round(p_ftm_a))}/{int(round(p_fta_a))}", f"{int(round(p_ftm_b))}/{int(round(p_fta_b))}", "  —"),
        ("FT%",   f".{int(round(p_ft_a*1000)):03d}", f".{int(round(p_ft_b*1000)):03d}", _prob_tag('FT_PCT')),
        ("3PTM",  f"{comb_berk['mean']['FG3M']:.1f}", f"{comb_opp['mean']['FG3M']:.1f}", _prob_tag('FG3M')),
        ("PTS",   f"{comb_berk['mean']['PTS']:.1f}",  f"{comb_opp['mean']['PTS']:.1f}",  _prob_tag('PTS')),
        ("REB",   f"{comb_berk['mean']['REB']:.1f}",  f"{comb_opp['mean']['REB']:.1f}",  _prob_tag('REB')),
        ("AST",   f"{comb_berk['mean']['AST']:.1f}",  f"{comb_opp['mean']['AST']:.1f}",  _prob_tag('AST')),
        ("ST",    f"{comb_berk['mean']['STL']:.1f}",  f"{comb_opp['mean']['STL']:.1f}",  _prob_tag('STL')),
        ("BLK",   f"{comb_berk['mean']['BLK']:.1f}",  f"{comb_opp['mean']['BLK']:.1f}",  _prob_tag('BLK')),
        ("TO",    f"{comb_berk['mean']['TOV']:.1f}",  f"{comb_opp['mean']['TOV']:.1f}",  _prob_tag('TOV')),
    ]
    box_lines.append("🔮 <b>HAFTA SONU FİNAL TAHMİNİ (Kalan Maçlar Dahil)</b>")
    pre_proj = [
        f"{'KAT':<5} {'BERK':>9} {opp_short:>10}  {'BERK%':<6}",
        "─" * 34,
    ]
    for c_name, v_a, v_b, w_p in proj_rows:
        pre_proj.append(f"{c_name:<5} {v_a:>9} {v_b:>10}  {w_p}")
    pre_proj.append("─" * 34)
    pre_proj.append(f"TAHMİN: Berk {exp_score:.2f} - {9.0 - exp_score:.2f} (%{matchup_win_prob*100:.0f})")
    box_lines.append("<pre>" + "\n".join(pre_proj) + "</pre>")

    msg_lines = [
        f"🏀 <b>NBA FANTASY GÜNLÜK ÖZET</b>",
        f"🗓 <i>{now_utc.strftime('%d.%m.%Y %H:%M UTC')} • {sync_badge}</i>",
        "",
        f"⚔️ <b>BERK'S BEST TEAM vs {opp_team_name}</b>",
        f"📊 <b>Tahmini Final:</b> <b>{exp_score:.2f} - {9.0 - exp_score:.2f}</b>  |  🎯 <b>Kazanma: %{matchup_win_prob*100:.0f}</b>",
        f"⏳ <b>Maçlar (Oynanan/Toplam • Kalan):</b>",
        f"• <b>Berk's Best Team:</b> <code>{gp_a}/{tot_a}</code> Oynandı • <b>{rem_a} Kalan</b>",
        f"• <b>{opp_team_name}:</b> <code>{gp_b}/{tot_b}</code> Oynandı • <b>{rem_b} Kalan</b>",
        "",
        *box_lines,
        "",
        f"🟢 <b>Üstün:</b> {' • '.join(strong_cats) if strong_cats else '—'}",
        f"⚖️ <b>Kritik:</b> {' • '.join(tossup_cats) if tossup_cats else '—'}",
        f"🔴 <b>Geride:</b> {' • '.join(weak_cats) if weak_cats else '—'}",
        "",
        "🏥 <b>KADRO & IL+ DURUMU</b>",
    ]
    if out_items:
        for it in out_items:
            il_hint = "IL+'da" if it['slot_state'] == "IL+" else "➔ IL+'a çek (Boş yuva açılır)"
            msg_lines.append(f"• ❌ <b>{it['name']}</b> (OUT) <i>{il_hint}</i>")
    else:
        msg_lines.append("• ✅ Kadroda OUT oyuncu yok")
    for it in gtd_items:
        msg_lines.append(f"• ⚠️ <b>{it['name']}</b> ({it['status']} • %{it['eff_avail']*100:.0f} Oynama)")

    msg_lines.extend([
        "",
        "🎯 <b>EN İYİ HAMLE ÖNERİLERİ (Kalan Maç & Skor Odaklı)</b>",
    ])
    rank_icons = ["1️⃣", "2️⃣", "3️⃣"]
    for idx_m, rec in enumerate(add_drop_recs[:3]):
        r_ico = rank_icons[idx_m] if idx_m < len(rank_icons) else f"<b>#{idx_m+1}</b>"
        bp_add = assistant.players.get(rec['add_id'])
        m_info = ""
        if bp_add:
            bm_a = getattr(bp_add, 'base_expected_minutes', bp_add.expected_minutes)
            bst = bp_add.expected_minutes - bm_a
            m_info = f" ({bp_add.expected_minutes:.1f} dk, {bst:+.1f}🔼)" if abs(bst) >= 0.5 else f" ({bp_add.expected_minutes:.1f} dk)"
        drop_lbl = "Boş Yuva (IL+)" if rec['drop_id'] is None else f"-{rec['drop_name']}"
        clean_gains = rec['key_cat_gains'].replace('_PCT', '%').replace('FG3M', '3PT')
        msg_lines.append(f"{r_ico} <b>+{rec['add_name']}</b>{m_info}")
        msg_lines.append(f"   └ 📥 {drop_lbl} • 📈 <b>{rec['delta_expected_wins']:+.2f} Kat.</b> <i>({clean_gains})</i>")

    # Top Free Agents (clean 1-line summary)
    top_fa_strs = []
    for pid_f, name_f, z_f, av_f, dropped_f in healthy_free_agents[:4]:
        bp_f = assistant.players[pid_f]
        bm_f = getattr(bp_f, 'base_expected_minutes', bp_f.expected_minutes)
        bst_f = bp_f.expected_minutes - bm_f
        tag_f = "🔥Yeni Düştü" if dropped_f else (f"{bp_f.expected_minutes:.0f}dk {bst_f:+.0f}🔼" if abs(bst_f) >= 1.0 else f"{bp_f.expected_minutes:.0f}dk")
        top_fa_strs.append(f"<b>{name_f}</b> ({tag_f})")

    msg_lines.extend([
        "",
        f"📋 <b>Boştaki Formda FA:</b> {' • '.join(top_fa_strs)}",
    ])

    if recent_transactions:
        msg_lines.extend(["", "🔄 <b>SON LİG HAMLELERİ</b>"])
        for tx in recent_transactions[:3]:
            a_n = ", ".join(f"+{x['player_name']}" for x in tx.get('added', []))
            d_n = ", ".join(f"-{x['player_name']}" for x in tx.get('dropped', []))
            t_n = tx['added'][0]['team_name'] if tx.get('added') else (tx['dropped'][0]['team_name'] if tx.get('dropped') else "")
            moves_joined = " / ".join(x for x in (a_n, d_n) if x)
            msg_lines.append(f"• <b>{t_n}:</b> {moves_joined}")

    if tg_token and tg_chat:
        try:
            import urllib.parse
            import urllib.request
            tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            tg_payload = urllib.parse.urlencode({
                "chat_id": tg_chat,
                "text": "\n".join(msg_lines),
                "parse_mode": "HTML",
                "disable_web_page_preview": "true"
            }).encode("utf-8")
            with urllib.request.urlopen(urllib.request.Request(tg_url, data=tg_payload, method="POST"), timeout=8.0) as resp:
                if resp.status == 200:
                    print("  [TELEGRAM] Zenginlestirilmis bildirim basariyla gonderildi!")
        except Exception as e:
            print(f"  [TELEGRAM] Bildirim hatasi: {e}")

    if discord_webhook:
        try:
            import urllib.request
            plain_md = (
                "\n".join(msg_lines)
                .replace("<b>", "**").replace("</b>", "**")
                .replace("<i>", "*").replace("</i>", "*")
                .replace("<code>", "`").replace("</code>", "`")
                .replace("<pre>", "```\n").replace("</pre>", "\n```")
            )
            disc_payload = json.dumps({"content": plain_md[:1990]}).encode("utf-8")
            req_d = urllib.request.Request(
                discord_webhook,
                data=disc_payload,
                headers={"Content-Type": "application/json", "User-Agent": "NBAFantasyBot/2.0"},
                method="POST"
            )
            with urllib.request.urlopen(req_d, timeout=8.0) as resp_d:
                if resp_d.status in (200, 204):
                    print("  [DISCORD] Webhook bildirimi basariyla gonderildi!")
        except Exception as e:
            print(f"  [DISCORD] Webhook hatasi: {e}")

    print("\n✅ CLOUD SYNC RUN COMPLETED SUCCESSFULLY.")

if __name__ == '__main__':
    run_cloud_sync()
