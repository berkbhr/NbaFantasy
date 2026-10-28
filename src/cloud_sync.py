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

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

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
from src.injury_tracker import InjuryTracker
from src.live_draft_assistant import LiveDraftAssistant
from src.nba_injury_scraper import (
    NBAOfficialInjuryScraper,
    _default_fetch_bytes,
    candidate_report_urls,
    extract_text_from_pdf,
    parse_report_text,
)
from src.season_logs import fetch_current_season_logs
from src.settings import load_settings
from src.snapshots import fantasy_week_window
from src.yahoo_draft_sync import YahooFantasyOAuthClient


def current_fantasy_week_window(now_utc, live_week_started=True):
    return fantasy_week_window(now_utc, live_week_started)


def run_cloud_sync():
    settings = load_settings()
    started = last_phase = perf_counter()

    def timing(label):
        nonlocal last_phase
        current = perf_counter()
        print(
            f"  [TIMING] {label}: {current - last_phase:.3f}s; total={current - started:.3f}s",
            flush=True,
        )
        last_phase = current

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

    parsed = {"rows": [], "unsubmitted_teams": [], "unparsed_lines": []}
    if raw_pdf_bytes:
        # Save rolling buffer (only 1 single file on disk, zero clutter)
        rolling_pdf_path = os.path.join(DATA_DIR, "raw", "injuries", "latest_official_report.pdf")
        os.makedirs(os.path.dirname(rolling_pdf_path), exist_ok=True)
        try:
            with open(rolling_pdf_path, "wb") as f:
                f.write(raw_pdf_bytes)
        except Exception:
            pass

        # Extract text in-memory
        full_text = extract_text_from_pdf(raw_pdf_bytes)
        parsed = parse_report_text(full_text)
        print(f"  Report Time: {parsed.get('report_time_utc')}")
        print(f"  Official Injury Rows Parsed: {len(parsed.get('rows', []))}")
        print(f"  Unsubmitted Teams: {[t['team'] for t in parsed.get('unsubmitted_teams', [])]}")
    else:
        print(
            "  [WARN] No live report PDF found on CDN in recent window. Using cached injuries.db."
        )

    # -------------------------------------------------------------------------
    # STEP 2: INITIALIZE ASSISTANT & RESOLVE PLAYER IDS
    # -------------------------------------------------------------------------
    timing("official_injury_report")
    print("\n[STEP 2] Initializing assistant & draft rosters...")
    # Replay completed observations chronologically before producing forecasts.
    season_logs_df, season_logs_src = fetch_current_season_logs(
        season="2026-27", timeout=10, retries=1
    )
    print(f"  Current-season logs: {len(season_logs_df)} player-games (source: {season_logs_src})")
    try:
        from src.game_clock import refresh_schedule

        refresh_schedule()
    except Exception as exc:
        print(
            f"  [CLOCK] Exact schedule refresh unavailable ({type(exc).__name__}); cached guards apply"
        )
    assistant = LiveDraftAssistant(
        prior_season="2025_26",
        my_team_idx=draft_data.MY_TEAM_IDX,
        num_teams=draft_data.NUM_TEAMS,
        objective=settings.objective,
        draw_value=settings.draw_value,
    )
    current_team_map = {}
    if not season_logs_df.empty:
        current_team_map = assistant.apply_current_season_logs(season_logs_df)
        print(
            f"  Applied in-season Bayesian updates for {len(current_team_map)} players "
            f"(through {pd.to_datetime(season_logs_df['GAME_DATE']).max().date()})."
        )
    else:
        print("  [WARN] No current-season logs available; projections use prior-season data only.")
    rosters = draft_data.resolve_rosters(assistant)
    berk_pids = rosters[draft_data.MY_TEAM_IDX]
    all_drafted_pids = set(p for slot in rosters for p in rosters[slot])

    def resolver(name):
        return assistant.resolve_player_id(name, only_available=False)

    # Synchronize all 30 teams from ESPN / Rotowire public API (covers multi-week & off-day injuries)
    try:
        espn_count = tracker.sync_espn_injuries(resolver)
        print(f"  Synchronized {espn_count} league-wide injuries from 30-team ESPN/Rotowire feed.")
    except Exception as e:
        print(f"  [WARN] ESPN injury sync: {e}")

    # The current official report takes precedence over the broader ESPN feed.
    updated_db_count = tracker.sync_official_report(parsed, resolver, scraper)
    if raw_pdf_bytes:
        from src.prospective import archive_official_snapshot

        healthy, _, _, _ = scraper.run_health_checks(parsed, id_resolver_fn=resolver)
        archive_official_snapshot(parsed, source_url, raw_pdf_bytes, accepted_for_live=healthy)
    print(f"  Synchronized {updated_db_count} validated official injuries.")

    # Also load all active injuries from DB into assistant.players
    from src.injury_tracker import normalize_name

    active_db = tracker.get_all_active_injuries()
    for item in active_db:
        pid = item["player_id"]
        if pid in assistant.players:
            assistant.players[pid].update_injury_status(
                item["status"], desc=item.get("injury_desc", "")
            )
        else:
            norm_target = normalize_name(item["player_name"])
            for p in assistant.players.values():
                if normalize_name(p.name) == norm_target:
                    p.update_injury_status(item["status"], desc=item.get("injury_desc", ""))
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
    timing("season_logs_clock_players_and_injuries")
    print(
        "\n[STEP 3] Synchronizing Live Yahoo League State (Rosters, IL+, Transactions, Scoreboard)..."
    )
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
            with open(state_json_path, "r", encoding="utf-8") as f:
                prior_state = json.load(f)
        except Exception:
            prior_state = {}

    live_rosters_synced = False
    if (
        yahoo_client.client_id
        and yahoo_client.client_secret
        and (yahoo_client.refresh_token or yahoo_client.access_token)
    ):
        if yahoo_client.discover_league_and_team(target_league_id="64691"):
            roster_payload = yahoo_client.fetch_league_rosters_and_il()
            if roster_payload and roster_payload.get("rosters_by_slot"):
                from src.yahoo_identity import roster_player_evidence, team_slots

                mapping, _ = team_slots(
                    roster_payload["rosters_by_slot"],
                    prior_state.get("yahoo_team_slots", {}),
                    roster_payload.get("team_names_by_slot", {}),
                )
                prior_state["yahoo_team_slots"] = mapping
                prior_state["yahoo_roster_players"] = roster_player_evidence(
                    roster_payload["rosters_by_slot"], mapping
                )
                for field in (
                    "rosters_by_slot",
                    "il_players_by_slot",
                    "unslotted_injured_by_slot",
                    "empty_active_slots_by_slot",
                ):
                    roster_payload[field] = {
                        int(mapping[str(int(k) + 1)]): v
                        for k, v in roster_payload.get(field, {}).items()
                    }
                new_rosters = {}
                for slot_idx, p_list in roster_payload["rosters_by_slot"].items():
                    resolved_pids = []
                    for p_item in p_list:
                        pid = assistant.resolve_player_id(p_item["name"], only_available=False)
                        if pid is not None and pid in assistant.players:
                            resolved_pids.append(pid)
                            if p_item.get("selected_position") in ("IL", "IL+") or p_item.get(
                                "status"
                            ) in ("IL", "INJ", "O", "OUT"):
                                yahoo_il_eligible_pids.add(pid)
                    if resolved_pids:
                        new_rosters[int(slot_idx)] = resolved_pids
                if len(new_rosters) == draft_data.NUM_TEAMS:
                    prior_state["sync_id"] = "oauth:" + now_utc.isoformat()
                    for s_idx, pids_list in new_rosters.items():
                        rosters[s_idx] = pids_list
                    il_players_by_slot = roster_payload.get(
                        "il_players_by_slot", il_players_by_slot
                    )
                    unslotted_injured_by_slot = roster_payload.get(
                        "unslotted_injured_by_slot", unslotted_injured_by_slot
                    )
                    empty_active_slots_by_slot = roster_payload.get(
                        "empty_active_slots_by_slot", empty_active_slots_by_slot
                    )
                    live_rosters_synced = True
                    yahoo_status_msg = f"OAuth2 Live Sync Active (League {yahoo_client.league_key})"
                    print(
                        f"  [OK] {yahoo_status_msg}: Synced {len(new_rosters)} team rosters & IL slots."
                    )
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
                        for d_item in tx.get("dropped", []):
                            d_pid = assistant.resolve_player_id(
                                d_item.get("player_name", ""), only_available=False
                            )
                            if d_pid is not None:
                                for s_idx in rosters:
                                    if d_pid in rosters[s_idx]:
                                        rosters[s_idx].remove(d_pid)
                        for a_item in tx.get("added", []):
                            a_pid = assistant.resolve_player_id(
                                a_item.get("player_name", ""), only_available=False
                            )
                            t_name = a_item.get("team_name", "").lower()
                            if a_pid is not None:
                                for s_idx, canonical_tname in enumerate(draft_data.TEAM_NAMES):
                                    if (
                                        canonical_tname.lower() in t_name
                                        or t_name in canonical_tname.lower()
                                    ):
                                        if a_pid not in rosters[s_idx]:
                                            rosters[s_idx].append(a_pid)
                    live_rosters_synced = True
                    yahoo_status_msg = (
                        f"OAuth2 Live Transactions Synced (League {yahoo_client.league_key})"
                    )

            sb_payload = yahoo_client.fetch_live_scoreboard()
            if sb_payload:
                from src.yahoo_identity import canonical_scoreboard

                sb_payload = canonical_scoreboard(
                    sb_payload, prior_state.get("yahoo_team_slots", {})
                )
            if sb_payload and sb_payload.get("matchups"):
                print(f"  [OK] Fetched Live Scoreboard for Week {sb_payload.get('week')}.")
                # Locate Berk's matchup
                berk_matchup = None
                for pair in sb_payload["matchups"]:
                    names_lower = [p.get("name", "").lower() for p in pair]
                    slots_pair = [p.get("slot", 0) for p in pair]
                    if (
                        any("berk" in n for n in names_lower)
                        or (draft_data.MY_TEAM_IDX + 1) in slots_pair
                    ):
                        if "berk" in names_lower[1] or slots_pair[1] == (
                            draft_data.MY_TEAM_IDX + 1
                        ):
                            pair = [pair[1], pair[0]]
                        berk_matchup = {
                            "week": sb_payload.get("week", 1),
                            "updated_at": now_utc.isoformat(),
                            "sync_id": prior_state.get("sync_id") if live_rosters_synced else None,
                            "matchup": {
                                "team_a": pair[0],
                                "team_b": pair[1],
                            },
                            "all_matchups": sb_payload["matchups"],
                        }
                        break
                if berk_matchup:
                    live_matchup_path = os.path.join(PROCESSED_DIR, "live_matchup.json")
                    try:
                        with open(live_matchup_path, "w", encoding="utf-8") as f:
                            json.dump(berk_matchup, f, indent=2)
                    except Exception:
                        pass
        else:
            yahoo_status_msg = f"OAuth2 configured, but league discovery returned False ({yahoo_client.last_error or 'check token/league'})"
            print(f"  [WARN] {yahoo_status_msg}")
    else:
        yahoo_status_msg = "OAuth2 Secret Eksik (GitHub Secrets -> YAHOO_OAUTH_JSON kontrol edin)"
        print(
            "  [INFO] No Yahoo OAuth2 credentials found in config/yahoo_oauth.json or YAHOO_OAUTH_JSON env."
        )

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
                else:
                    print(
                        f"  [WARN] Roster player '{p_name}' could not be resolved in slot {s_idx}!"
                    )
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
            yahoo_status_msg = prior_state.get(
                "sync_status", "Tarayıcı Köprüsü Aktif (14 Takım Canlı Kadro)"
            )
            print(f"  [OK] Loaded live league state from league_state.json ({yahoo_status_msg}).")

    if not recent_transactions and prior_state.get("transactions"):
        recent_transactions = prior_state.get("transactions", [])

    # Missing roster rows, including IL/IL+, do not prove a player was dropped.
    initial_draft_rosters = draft_data.resolve_rosters(assistant)
    initial_draft_pids = {p for roster in initial_draft_rosters.values() for p in roster}
    from src.ownership import free_agent_ids

    verified_fa_pids, ownership_audit = free_agent_ids(assistant, prior_state, rosters, now_utc)
    if ownership_audit["reason"]:
        print("  [OWNERSHIP] " + ownership_audit["reason"])

    # Refresh Berk's roster & all_rostered_pids after live roster / transaction updates
    berk_pids = rosters[draft_data.MY_TEAM_IDX]
    all_drafted_pids = set(p for slot in rosters for p in rosters[slot])

    # A roster disappearance is not a confirmed drop/free-agent event.
    dropped_to_fa_pids = sorted(initial_draft_pids & verified_fa_pids, key=str)

    newly_added_from_fa_pids = [pid for pid in all_drafted_pids if pid not in initial_draft_pids]

    league_state = {
        "updated_at": now_utc.isoformat(),
        "league_id": "64691",
        "league_key": yahoo_client.league_key or "nba.l.64691",
        "live_synced": bool(live_rosters_synced),
        "sync_status": yahoo_status_msg,
        "rosters": {
            str(slot): [assistant.players[p].name for p in pids if p in assistant.players]
            for slot, pids in rosters.items()
        },
        "berk_roster_names": [
            assistant.players[p].name for p in berk_pids if p in assistant.players
        ],
        "il_slots": {str(slot): names for slot, names in il_players_by_slot.items()},
        "unslotted_injured": {
            str(slot): items for slot, items in unslotted_injured_by_slot.items()
        },
        "empty_active_slots": {str(slot): cnt for slot, cnt in empty_active_slots_by_slot.items()},
        "transactions": recent_transactions[:25],
        "dropped_free_agents": [
            assistant.players[p].name for p in dropped_to_fa_pids if p in assistant.players
        ],
        "added_streamers": [
            assistant.players[p].name for p in newly_added_from_fa_pids if p in assistant.players
        ],
        "waivers": prior_state.get("waivers", {}),
        "availability_snapshot": prior_state.get("availability_snapshot", {}),
        "ownership_audit": ownership_audit,
        "yahoo_team_slots": prior_state.get("yahoo_team_slots", {}),
        "sync_id": prior_state.get("sync_id"),
        "yahoo_roster_players": prior_state.get("yahoo_roster_players", {}),
        "capture_metrics": prior_state.get("capture_metrics", {}),
    }

    # Save state JSON
    try:
        with open(state_json_path, "w", encoding="utf-8") as f:
            json.dump(league_state, f, indent=2)
    except Exception:
        pass

    timing("yahoo_state")
    # One canonical forecast is archived, rendered and delivered. The old
    # path computed and then discarded another full set of recommendations.
    summary_path = os.path.join(REPORTS_DIR, "latest_cloud_summary.md")
    from src.prospective import record_run, settle_weekly

    # Record predictions before notification; never overwrite forecasts with outcomes.
    prospective = record_run(fetch_results=True)
    settle_weekly(yahoo_client=yahoo_client if yahoo_client.league_key else None)
    timing("canonical_forecast_archive_and_settlement")
    print(f"  Archived prospective forecast: {prospective['prospective_forecast_id']}")

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
                with open(tg_conf_path, "r", encoding="utf-8") as f:
                    tg_conf = json.load(f)
                    tg_token = tg_token or str(tg_conf.get("bot_token", "")).strip()
                    tg_chat = tg_chat or str(tg_conf.get("chat_id", "")).strip()
                    discord_webhook = (
                        discord_webhook or str(tg_conf.get("discord_webhook_url", "")).strip()
                    )
            except Exception:
                pass

    from src.forecast import render_report
    from src.notifications import DeliveryError, render_preview, render_telegram, send_telegram
    from src.probability import CategoryProbabilities
    from src.prospective import ARCHIVE, write_once

    canonical_probs = CategoryProbabilities(
        {c: v["win"] for c, v in prospective["categories"].items()}
    )
    canonical_probs.ties.update({c: v["tie"] for c, v in prospective["categories"].items()})
    with open(os.path.join(REPORTS_DIR, "latest_forecast.json"), "w", encoding="utf-8") as handle:
        json.dump(prospective, handle, indent=2, ensure_ascii=False, default=str)
    with open(summary_path, "w", encoding="utf-8") as handle:
        handle.write(render_report(prospective))

    gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh_summary:
        with open(gh_summary, "a", encoding="utf-8") as handle:
            handle.write(render_report(prospective))

    notification = render_telegram(
        now=pd.Timestamp(prospective["forecast_at"]).to_pydatetime(),
        opponent=prospective["opponent"],
        points=prospective["objective_value"],
        probabilities=canonical_probs,
        health=prospective["roster_health"],
        recommendations=prospective["recommendations"],
        live=prospective["live_score"],
        objective=prospective["objective"],
        ownership_audit=prospective.get("ownership_audit"),
        live_score_block_reason=prospective.get("live_score_block_reason"),
    )
    preview_path = os.path.join(REPORTS_DIR, "telegram_preview.html")
    with open(preview_path, "w", encoding="utf-8") as handle:
        handle.write(render_preview(notification))

    prediction_file = (
        ARCHIVE / "predictions" / (prospective["prospective_forecast_id"] + ".json.gz")
    )
    delivery = {
        "forecast_id": prospective["prospective_forecast_id"],
        "status": "not_configured",
        "receipts": [],
        "prediction_sha256": hashlib.sha256(prediction_file.read_bytes()).hexdigest(),
        "rendered_text_sha256": hashlib.sha256(notification.encode()).hexdigest(),
        "source_revision": os.environ.get("GITHUB_SHA"),
        "renderer_sha256_LF": hashlib.sha256(
            (Path(SRC_DIR) / "notifications.py").read_text(encoding="utf-8").encode()
        ).hexdigest(),
    }
    dry_run = os.environ.get("NBA_FANTASY_DRY_RUN", "").lower() == "true"
    if dry_run:
        delivery["status"] = "disabled_for_validation"
    if tg_token and tg_chat and not dry_run:
        try:
            delivery["receipts"] = send_telegram(tg_token, tg_chat, notification)
            delivery["status"] = "api_accepted"
            print(
                f"  [TELEGRAM] API accepted {len(delivery['receipts'])} message part(s); forecast={delivery['forecast_id']}"
            )
        except DeliveryError as exc:
            delivery["status"] = "failed"
            delivery["receipts"] = exc.receipts
            delivery["error"] = str(exc)
            print("  [TELEGRAM] Delivery failed; safe receipt saved")
    write_once(ARCHIVE / "notifications" / (delivery["forecast_id"] + ".json.gz"), delivery)
    with open(os.path.join(REPORTS_DIR, "delivery_receipt.json"), "w", encoding="utf-8") as handle:
        json.dump(delivery, handle, indent=2)

    if discord_webhook and not dry_run:
        try:
            import urllib.request

            plain_md = (
                notification.replace("<b>", "**")
                .replace("</b>", "**")
                .replace("<i>", "*")
                .replace("</i>", "*")
                .replace("<code>", "`")
                .replace("</code>", "`")
                .replace("<pre>", "```\n")
                .replace("</pre>", "\n```")
            )
            disc_payload = json.dumps({"content": plain_md[:1990]}).encode("utf-8")
            req_d = urllib.request.Request(
                discord_webhook,
                data=disc_payload,
                headers={"Content-Type": "application/json", "User-Agent": "NBAFantasyBot/2.0"},
                method="POST",
            )
            with urllib.request.urlopen(req_d, timeout=8.0) as resp_d:
                if resp_d.status in (200, 204):
                    print("  [DISCORD] Webhook bildirimi basariyla gonderildi!")
        except Exception as e:
            print(f"  [DISCORD] Webhook hatasi: {e}")

    if delivery["status"] == "failed":
        raise RuntimeError("Telegram delivery failed; forecast and receipt retained")
    timing("report_and_delivery")
    print("\n✅ CLOUD SYNC RUN COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    run_cloud_sync()
