import os
import sys
import json
import time
import base64
import threading
import urllib.request
import urllib.parse
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
OAUTH_CONFIG_PATH = os.path.join(CONFIG_DIR, 'yahoo_oauth.json')


class YahooFantasyOAuthClient:
    """
    Lightweight, zero-dependency Yahoo Fantasy Sports OAuth2 REST API client.
    Features:
      - Automatic token refresh (`refresh_access_token`) before/upon HTTP 401 expiration
        so a 1-hour OAuth token expiry mid-draft never interrupts live syncing.
      - Non-blocking error handling: if network or token fails, logs a warning and falls back
        seamlessly to the Browser Bridge (`127.0.0.1:8765`) and Manual CLI (`pick` / `my_pick`).
    """

    TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
    API_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"

    def __init__(self, config_path=OAUTH_CONFIG_PATH):
        self.config_path = config_path
        self.client_id = ""
        self.client_secret = ""
        self.refresh_token = ""
        self.access_token = ""
        self.token_expiry = 0.0
        self.league_key = ""
        self.team_key = ""
        self.last_error = None
        self.load_config()

    def load_config(self):
        data = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                self.last_error = f"Config okuma hatası: {e}"

        # Support headless GitHub Actions environment secrets (`YAHOO_OAUTH_JSON` or individual env vars)
        env_oauth_json = os.environ.get("YAHOO_OAUTH_JSON", "").strip()
        if env_oauth_json:
            try:
                env_data = json.loads(env_oauth_json)
                if isinstance(env_data, dict):
                    data.update({k: v for k, v in env_data.items() if v})
            except Exception:
                pass

        self.client_id = str(os.environ.get('YAHOO_CLIENT_ID') or data.get('client_id', '')).strip()
        self.client_secret = str(os.environ.get('YAHOO_CLIENT_SECRET') or data.get('client_secret', '')).strip()
        self.refresh_token = str(os.environ.get('YAHOO_REFRESH_TOKEN') or data.get('refresh_token', '')).strip()
        self.access_token = str(os.environ.get('YAHOO_ACCESS_TOKEN') or data.get('access_token', '')).strip()
        try:
            self.token_expiry = float(data.get('token_expiry', 0.0))
        except (TypeError, ValueError):
            self.token_expiry = 0.0
        self.league_key = str(os.environ.get('YAHOO_LEAGUE_KEY') or data.get('league_key', '')).strip()
        self.team_key = str(os.environ.get('YAHOO_TEAM_KEY') or data.get('team_key', '')).strip()
        return bool(self.client_id and self.client_secret and (self.refresh_token or self.access_token))

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'access_token': self.access_token,
            'token_expiry': self.token_expiry,
            'league_key': self.league_key,
            'team_key': self.team_key,
        }
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            self.last_error = f"Config yazma hatası: {e}"

    def is_configured(self):
        return bool(self.league_key and (self.access_token or (self.client_id and self.client_secret and self.refresh_token)))

    def refresh_access_token(self):
        if not (self.client_id and self.client_secret and self.refresh_token):
            self.last_error = "OAuth2 refresh_token veya client_id/secret eksik."
            return False
        try:
            creds = f"{self.client_id}:{self.client_secret}".encode('utf-8')
            b64_auth = base64.b64encode(creds).decode('ascii')
            body = urllib.parse.urlencode({
                'grant_type': 'refresh_token',
                'redirect_uri': 'oob',
                'refresh_token': self.refresh_token,
            }).encode('utf-8')
            req = urllib.request.Request(
                self.TOKEN_URL,
                data=body,
                headers={
                    'Authorization': f'Basic {b64_auth}',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
            self.access_token = resp_data.get('access_token', self.access_token)
            self.refresh_token = resp_data.get('refresh_token', self.refresh_token)
            expires_in = float(resp_data.get('expires_in', 3600))
            self.token_expiry = time.time() + expires_in - 60.0
            self.save_config()
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = f"Token yenileme hatası: {e}"
            return False

    def _api_get(self, endpoint_path, timeout=3.5):
        if not self.access_token or (self.token_expiry > 0 and time.time() >= self.token_expiry):
            self.refresh_access_token()

        url = f"{self.API_BASE}/{endpoint_path.lstrip('/')}"
        if '?' not in url:
            url += "?format=json"
        elif 'format=json' not in url:
            url += "&format=json"

        for attempt in range(2):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        'Authorization': f'Bearer {self.access_token}',
                        'Accept': 'application/json',
                        'User-Agent': 'NBAFantasyAssistant/1.0',
                    },
                    method='GET',
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode('utf-8')
                    self.last_error = None
                    return json.loads(raw)
            except urllib.error.HTTPError as he:
                if he.code == 401 and attempt == 0:
                    if self.refresh_access_token():
                        continue
                self.last_error = f"Yahoo HTTP {he.code}: {he.reason}"
                return None
            except Exception as e:
                self.last_error = f"Yahoo bağlantı hatası: {e}"
                return None
        return None

    def fetch_live_draft_picks(self):
        """
        Fetches `/league/{league_key}/draftresults;out=players?format=json` from Yahoo API
        and extracts completed picks as `[{'pick': int, 'player_name': str, 'team_key': str}, ...]`.
        """
        if not self.is_configured():
            return []
        data = self._api_get(f"league/{self.league_key}/draftresults;out=players")
        if not data:
            return []

        picks_out = []
        try:
            fc = data.get('fantasy_content', {})
            league_arr = fc.get('league', [])
            if len(league_arr) < 2:
                return []
            draft_res = league_arr[1].get('draft_results', {})
            for k, v in draft_res.items():
                if k == 'count' or not isinstance(v, dict):
                    continue
                dr = v.get('draft_result', {})
                pick_num = int(dr.get('pick', 0))
                player_name = None

                # Extract player full name if `;out=players` subresource is included
                players_sub = dr.get('players', {})
                if isinstance(players_sub, dict) and '0' in players_sub:
                    p_arr = players_sub['0'].get('player', [])
                    if p_arr and isinstance(p_arr[0], list):
                        for item in p_arr[0]:
                            if isinstance(item, dict) and 'name' in item:
                                player_name = item['name'].get('full')
                                break

                if not player_name and 'player_name' in dr:
                    player_name = dr.get('player_name')

                if pick_num > 0 and player_name:
                    picks_out.append({
                        'pick': pick_num,
                        'player_name': str(player_name).strip(),
                        'team_key': dr.get('team_key', ''),
                    })
            picks_out.sort(key=lambda x: x['pick'])
        except Exception as e:
            self.last_error = f"Draft JSON ayrıştırma hatası: {e}"
        return picks_out

    def discover_league_and_team(self, target_league_id="64691"):
        """
        Automatically resolves `self.league_key` (e.g. `454.l.64691` or `nba.l.64691`) and `self.team_key`
        using multi-stage fallback probing so it never fails even if `league_key` is blank in config.
        """
        if self.league_key and self.team_key:
            return True

        # Stage 1: Query all NBA game seasons associated with the logged-in Yahoo user
        for ep_query in (
            "users;use_login=1/games;game_codes=nba/leagues",
            "users;use_login=1/games;game_keys=nba/leagues",
        ):
            if self.league_key:
                break
            data = self._api_get(ep_query)
            if not data:
                continue
            try:
                fc = data.get("fantasy_content", {})
                users = fc.get("users", {})
                user_info = users.get("0", {}).get("user", [])
                games = user_info[1].get("games", {}) if len(user_info) > 1 else {}
                all_found_keys = []
                for gk, gv in games.items():
                    if gk == "count" or not isinstance(gv, dict):
                        continue
                    g_arr = gv.get("game", [])
                    leagues = g_arr[1].get("leagues", {}) if len(g_arr) > 1 else {}
                    for lk, lv in leagues.items():
                        if lk == "count" or not isinstance(lv, dict):
                            continue
                        l_info = lv.get("league", [])
                        meta = l_info[0] if l_info and isinstance(l_info[0], dict) else {}
                        l_key = str(meta.get("league_key", ""))
                        l_id = str(meta.get("league_id", ""))
                        if l_key:
                            all_found_keys.append(l_key)
                            if target_league_id and (l_id == str(target_league_id) or l_key.endswith(f".l.{target_league_id}")):
                                self.league_key = l_key
                                break
                    if self.league_key:
                        break
                if not self.league_key and all_found_keys:
                    # Pick the most recent season's league key (highest numeric game_id prefix)
                    all_found_keys.sort( reverse=True)
                    self.league_key = all_found_keys[0]
            except Exception as e:
                self.last_error = f"Lig keşif hatası (Stage 1): {e}"

        # Stage 2: Direct candidate league_key probing for league_id 64691 (covers current/recent NBA game IDs)
        if not self.league_key and target_league_id:
            for cand_prefix in ("nba", "466", "454", "428"):
                cand_key = f"{cand_prefix}.l.{target_league_id}"
                probe = self._api_get(f"league/{cand_key}/teams")
                if probe and "fantasy_content" in probe:
                    try:
                        l_arr = probe["fantasy_content"].get("league", [])
                        if l_arr and isinstance(l_arr[0], dict) and l_arr[0].get("league_key"):
                            self.league_key = str(l_arr[0]["league_key"])
                        else:
                            self.league_key = cand_key
                        break
                    except Exception:
                        self.league_key = cand_key
                        break

        if not self.league_key:
            return False

        # Stage 3: Discover user's team_key inside the resolved league
        try:
            t_data = self._api_get(f"league/{self.league_key}/teams")
            if t_data:
                t_fc = t_data.get("fantasy_content", {}).get("league", [])
                teams_obj = t_fc[1].get("teams", {}) if len(t_fc) > 1 else {}
                for tk, tv in teams_obj.items():
                    if tk == "count" or not isinstance(tv, dict):
                        continue
                    t_arr = tv.get("team", [])
                    if not t_arr:
                        continue
                    meta_list = t_arr[0] if isinstance(t_arr[0], list) else t_arr
                    t_name, curr_t_key, is_owned = "", "", False
                    for item in meta_list:
                        if isinstance(item, dict):
                            if "name" in item:
                                t_name = str(item["name"])
                            if "team_key" in item:
                                curr_t_key = str(item["team_key"])
                            if item.get("is_owned_by_current_login") == 1:
                                is_owned = True
                    if is_owned or "berk" in t_name.lower():
                        self.team_key = curr_t_key
                        break
            self.save_config()
            return True
        except Exception as e:
            self.last_error = f"Takım keşif hatası: {e}"
            return bool(self.league_key)

    def fetch_league_rosters_and_il(self):
        """
        Fetches all 14 teams' live rosters and slot assignments (`PG`, `UTIL`, `BN`, `IL`, `IL+`)
        via `/league/{league_key}/teams;out=roster`.
        Returns:
          {
            'rosters_by_slot': {0: [{'name': str, 'selected_position': str, 'status': str}, ...], ...},
            'team_names_by_slot': {0: str, ...},
            'team_keys_by_slot': {0: str, ...},
            'il_players_by_slot': {0: [str, ...], ...},
            'unslotted_injured_by_slot': {0: [{'name': str, 'status': str, 'slot': str}, ...], ...},
            'empty_active_slots_by_slot': {0: int, ...}
          }
        """
        if not self.league_key:
            self.discover_league_and_team()
        if not self.league_key:
            return None

        data = self._api_get(f"league/{self.league_key}/teams;out=roster", timeout=6.0)
        if not data:
            return None

        result = {
            'rosters_by_slot': {},
            'team_names_by_slot': {},
            'team_keys_by_slot': {},
            'il_players_by_slot': {},
            'unslotted_injured_by_slot': {},
            'empty_active_slots_by_slot': {},
        }
        try:
            league_arr = data.get("fantasy_content", {}).get("league", [])
            if len(league_arr) < 2:
                return None
            teams_obj = league_arr[1].get("teams", {})
            for tk, tv in teams_obj.items():
                if tk == "count" or not isinstance(tv, dict):
                    continue
                team_node = tv.get("team", [])
                if not team_node:
                    continue
                meta_list = team_node[0] if isinstance(team_node[0], list) else []
                t_id, t_key, t_name = None, "", ""
                for item in meta_list:
                    if isinstance(item, dict):
                        if "team_id" in item:
                            t_id = int(item["team_id"])
                        if "team_key" in item:
                            t_key = str(item["team_key"])
                        if "name" in item:
                            t_name = str(item["name"])
                if t_id is None:
                    continue
                slot_idx = t_id - 1
                result['team_names_by_slot'][slot_idx] = t_name
                result['team_keys_by_slot'][slot_idx] = t_key

                roster_obj = team_node[1].get("roster", {}) if len(team_node) > 1 else {}
                players_container = roster_obj.get("0", {}).get("players", {}) if "0" in roster_obj else roster_obj.get("players", {})

                team_players = []
                il_list = []
                unslotted_inj = []
                active_filled_count = 0

                if isinstance(players_container, dict):
                    for pk, pv in players_container.items():
                        if pk == "count" or not isinstance(pv, dict):
                            continue
                        p_node = pv.get("player", [])
                        if not p_node:
                            continue
                        p_meta = p_node[0] if isinstance(p_node[0], list) else []
                        p_name, p_status = "", "HEALTHY"
                        for m in p_meta:
                            if isinstance(m, dict):
                                if "name" in m and isinstance(m["name"], dict):
                                    p_name = str(m["name"].get("full", "")).strip()
                                if "status" in m and m["status"]:
                                    p_status = str(m["status"]).upper().strip()

                        sel_pos = "BN"
                        for sub in p_node[1:]:
                            if isinstance(sub, dict) and "selected_position" in sub:
                                sp_arr = sub["selected_position"]
                                if isinstance(sp_arr, list):
                                    for sp_item in sp_arr:
                                        if isinstance(sp_item, dict) and "position" in sp_item:
                                            sel_pos = str(sp_item["position"]).upper().strip()
                                elif isinstance(sp_arr, dict) and "position" in sp_arr:
                                    sel_pos = str(sp_arr["position"]).upper().strip()

                        if not p_name:
                            continue
                        team_players.append({
                            'name': p_name,
                            'selected_position': sel_pos,
                            'status': p_status,
                        })
                        if sel_pos in ('IL', 'IL+'):
                            il_list.append(p_name)
                        else:
                            if sel_pos not in ('BN', 'IL', 'IL+'):
                                active_filled_count += 1
                            if p_status in ('INJ', 'O', 'OUT', 'IL', 'GTD', 'DTD'):
                                unslotted_inj.append({
                                    'name': p_name,
                                    'status': p_status,
                                    'slot': sel_pos,
                                })

                result['rosters_by_slot'][slot_idx] = team_players
                result['il_players_by_slot'][slot_idx] = il_list
                result['unslotted_injured_by_slot'][slot_idx] = unslotted_inj
                # Standard 10 active slots; if total non-IL players < 13, empty roster spot exists
                non_il_count = len([x for x in team_players if x['selected_position'] not in ('IL', 'IL+')])
                result['empty_active_slots_by_slot'][slot_idx] = max(0, 13 - non_il_count)
            return result
        except Exception as e:
            self.last_error = f"Kadro/IL ayrıştırma hatası: {e}"
            return None

    def fetch_recent_transactions(self, count=25):
        """
        Fetches `/league/{league_key}/transactions;types=add,drop,trade` and returns chronological
        list of add/drop/trade moves:
          `[{'transaction_id': str, 'type': str, 'timestamp': int, 'added': [{'player_name': str, 'team_name': str, 'team_key': str}], 'dropped': [...]}, ...]`
        """
        if not self.league_key:
            self.discover_league_and_team()
        if not self.league_key:
            return []

        data = self._api_get(f"league/{self.league_key}/transactions;types=add,drop,trade;count={int(count)}", timeout=5.0)
        if not data:
            return []

        tx_list = []
        try:
            league_arr = data.get("fantasy_content", {}).get("league", [])
            if len(league_arr) < 2:
                return []
            tx_obj = league_arr[1].get("transactions", {})
            for k, v in tx_obj.items():
                if k == "count" or not isinstance(v, dict):
                    continue
                tx_node = v.get("transaction", [])
                if len(tx_node) < 2:
                    continue
                tx_meta = tx_node[0] if isinstance(tx_node[0], dict) else {}
                tx_id = str(tx_meta.get("transaction_id", ""))
                tx_type = str(tx_meta.get("type", ""))
                tx_time = int(tx_meta.get("timestamp", 0))
                players_obj = tx_node[1].get("players", {})
                added, dropped = [], []
                if isinstance(players_obj, dict):
                    for pk, pv in players_obj.items():
                        if pk == "count" or not isinstance(pv, dict):
                            continue
                        p_node = pv.get("player", [])
                        if not p_node:
                            continue
                        p_meta = p_node[0] if isinstance(p_node[0], list) else []
                        p_name = ""
                        for m in p_meta:
                            if isinstance(m, dict) and "name" in m and isinstance(m["name"], dict):
                                p_name = str(m["name"].get("full", "")).strip()
                        tx_data = {}
                        for sub in p_node[1:]:
                            if isinstance(sub, dict) and "transaction_data" in sub:
                                td = sub["transaction_data"]
                                tx_data = td[0] if isinstance(td, list) and td else (td if isinstance(td, dict) else {})
                        action_type = str(tx_data.get("type", "")).lower()
                        if action_type == "add":
                            added.append({
                                'player_name': p_name,
                                'team_key': str(tx_data.get("destination_team_key", "")),
                                'team_name': str(tx_data.get("destination_team_name", "")),
                                'source_type': str(tx_data.get("source_type", "")),
                            })
                        elif action_type == "drop":
                            dropped.append({
                                'player_name': p_name,
                                'team_key': str(tx_data.get("source_team_key", "")),
                                'team_name': str(tx_data.get("source_team_name", "")),
                                'destination_type': str(tx_data.get("destination_type", "")),
                            })
                if added or dropped:
                    tx_list.append({
                        'transaction_id': tx_id,
                        'type': tx_type,
                        'timestamp': tx_time,
                        'added': added,
                        'dropped': dropped,
                    })
            tx_list.sort(key=lambda x: x['timestamp'], reverse=True)
        except Exception as e:
            self.last_error = f"Transaction ayrıştırma hatası: {e}"
        return tx_list

    def fetch_live_scoreboard(self, week=None):
        """
        Fetches `/league/{league_key}/scoreboard` for the current (or specified) week and parses
        all 9-category H2H scores plus remaining/played games.
        Yahoo standard NBA stat_ids:
          '9004003': FGM/FGA, '5': FG%, '9007006': FTM/FTA, '8': FT%,
          '10': FG3M, '12': PTS, '15': REB, '16': AST, '17': STL, '18': BLK, '19': TOV
        """
        if not self.league_key:
            self.discover_league_and_team()
        if not self.league_key:
            return None

        ep = f"league/{self.league_key}/scoreboard" + (f";week={int(week)}" if week else "")
        data = self._api_get(ep, timeout=5.0)
        if not data:
            return None

        STAT_ID_MAP = {
            '10': 'FG3M',
            '12': 'PTS',
            '15': 'REB',
            '16': 'AST',
            '17': 'STL',
            '18': 'BLK',
            '19': 'TOV',
        }
        try:
            league_arr = data.get("fantasy_content", {}).get("league", [])
            if len(league_arr) < 2:
                return None
            sb = league_arr[1].get("scoreboard", {})
            curr_week = int(sb.get("week", week or 1))
            matchups_obj = sb.get("0", {}).get("matchups", {}) if "0" in sb else sb.get("matchups", {})

            parsed_matchups = []
            for mk, mv in matchups_obj.items():
                if mk == "count" or not isinstance(mv, dict):
                    continue
                m_node = mv.get("matchup", {})
                teams_container = m_node.get("0", {}).get("teams", {}) if "0" in m_node else m_node.get("teams", {})
                pair = []
                for tk in ("0", "1"):
                    if tk not in teams_container:
                        continue
                    t_node = teams_container[tk].get("team", [])
                    if len(t_node) < 2:
                        continue
                    t_meta = t_node[0] if isinstance(t_node[0], list) else []
                    t_name, t_id, t_key = "", 0, ""
                    for item in t_meta:
                        if isinstance(item, dict):
                            if "name" in item:
                                t_name = str(item["name"])
                            if "team_id" in item:
                                t_id = int(item["team_id"])
                            if "team_key" in item:
                                t_key = str(item["team_key"])

                    t_stats_wrapper = t_node[1] if isinstance(t_node[1], dict) else {}
                    rg_obj = t_stats_wrapper.get("remaining_games", {}).get("total", {})
                    if not rg_obj and "team_remaining_games" in t_stats_wrapper:
                        rg_obj = t_stats_wrapper.get("team_remaining_games", {}).get("total", {})

                    gp = int(rg_obj.get("completed_games", 0))
                    g_rem = int(rg_obj.get("remaining_games", 0)) + int(rg_obj.get("live_games", 0))

                    stats_dict = {
                        'name': t_name,
                        'slot': t_id,
                        'team_key': t_key,
                        'games_played': gp,
                        'games_remaining': g_rem,
                        'total_scheduled': max(gp + g_rem, 1),
                    }
                    raw_stats = t_stats_wrapper.get("team_stats", {}).get("stats", [])
                    for s_entry in raw_stats:
                        st_obj = s_entry.get("stat", {}) if isinstance(s_entry, dict) else {}
                        sid = str(st_obj.get("stat_id", ""))
                        val_str = str(st_obj.get("value", "0")).strip()
                        if sid in STAT_ID_MAP:
                            try:
                                stats_dict[STAT_ID_MAP[sid]] = float(val_str) if val_str and val_str != '-' else 0.0
                            except ValueError:
                                stats_dict[STAT_ID_MAP[sid]] = 0.0
                        elif sid == '9004003' or ('/' in val_str and 'FGM' not in stats_dict):
                            parts = val_str.split('/')
                            if len(parts) == 2:
                                try:
                                    stats_dict['FGM'] = float(parts[0])
                                    stats_dict['FGA'] = float(parts[1])
                                except ValueError:
                                    pass
                        elif sid == '9007006' or ('/' in val_str and 'FTM' not in stats_dict):
                            parts = val_str.split('/')
                            if len(parts) == 2:
                                try:
                                    stats_dict['FTM'] = float(parts[0])
                                    stats_dict['FTA'] = float(parts[1])
                                except ValueError:
                                    pass
                    pair.append(stats_dict)
                if len(pair) == 2:
                    parsed_matchups.append(pair)
            return {'week': curr_week, 'matchups': parsed_matchups}
        except Exception as e:
            self.last_error = f"Scoreboard ayrıştırma hatası: {e}"
            return None


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<title>🏀 Yahoo 2026-27 Canlı Draft Otopilot Paneli (Slot #8)</title>
<style>
  body { background:#0b0f19; color:#e2e8f0; font-family:'Segoe UI',system-ui,sans-serif; margin:0; padding:18px; }
  .header { display:flex; justify-content:space-between; align-items:center; background:#111827; padding:14px 20px; border-radius:10px; border:1px solid #1f2937; margin-bottom:16px; }
  .badge { padding:6px 12px; border-radius:6px; font-weight:700; font-size:13px; }
  .badge-turn { background:#059669; color:#fff; animation: pulse 1.2s infinite; }
  .badge-wait { background:#1e293b; color:#94a3b8; }
  @keyframes pulse { 0% { opacity:1; } 50% { opacity:0.65; } 100% { opacity:1; } }
  .grid { display:grid; grid-template-columns: 2fr 1fr; gap:16px; }
  .card { background:#111827; border:1px solid #1f2937; border-radius:10px; padding:16px; }
  h2, h3 { margin-top:0; color:#f8fafc; font-size:16px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th, td { padding:9px 10px; text-align:left; border-bottom:1px solid #1f2937; }
  th { color:#94a3b8; font-weight:600; }
  tr:hover { background:#1e293b; }
  .win-score { color:#34d399; font-weight:700; font-size:14px; }
  .btn { background:#2563eb; color:#fff; border:none; padding:6px 12px; border-radius:5px; cursor:pointer; font-weight:600; font-size:12px; }
  .btn:hover { background:#1d4ed8; }
  .btn-undo { background:#dc2626; }
  .input-bar { display:flex; gap:8px; margin-top:12px; }
  input[type="text"] { flex:1; background:#0f172a; border:1px solid #334155; color:#fff; padding:8px 12px; border-radius:6px; }
</style>
</head>
<body>
  <div class="header">
    <div>
      <div style="font-size:18px;font-weight:800;">🏀 YAHOO 2026-27 CANLI DRAFT ASİSTANI — SLOT #<span id="my-slot">8</span></div>
      <div style="font-size:12px;color:#94a3b8;margin-top:4px;" id="sync-info">Canlı Köprü Aktif (127.0.0.1:8765)</div>
    </div>
    <div id="turn-badge" class="badge badge-wait">Yükleniyor...</div>
  </div>
  <div class="grid">
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <h3>🎯 Sıradaki Seçim İçin En İyi Öneriler (Pairwise H2H Rollout + FastZ)</h3>
        <span id="calc-speed" style="font-size:12px;color:#38bdf8;"></span>
      </div>
      <table>
        <thead>
          <tr><th>#</th><th>Oyuncu</th><th>Takım/Poz</th><th>E[Wins]/9</th><th>FastZ</th><th>BaseZ</th><th>Aktif Punt</th><th>Manuel İşlem</th></tr>
        </thead>
        <tbody id="rec-tbody"></tbody>
      </table>
      <div class="input-bar">
        <input type="text" id="manual-input" placeholder="Manuel Yedek: Seçilen oyuncu adını yazın (Örn: Jokic veya Maxey)..." />
        <button class="btn" onclick="submitManualPick(false)">Sıradaki Takıma İşle (pick)</button>
        <button class="btn" style="background:#059669;" onclick="submitManualPick(true)">Kadroma Ekle (my_pick)</button>
        <button class="btn btn-undo" onclick="undoPick()">Geri Al (undo)</button>
      </div>
    </div>
    <div class="card">
      <h3>📋 Kadromuz (<span id="roster-count">0</span>/13) & Kategori Kazanma Olasılıkları</h3>
      <div id="cat-probs" style="margin-bottom:12px;font-size:12px;line-height:1.7;"></div>
      <ul id="my-roster-list" style="padding-left:18px;font-size:13px;line-height:1.6;"></ul>
      <h3 style="margin-top:16px;">🕒 Son Yapılan Seçimler</h3>
      <ul id="recent-picks" style="padding-left:18px;font-size:12px;color:#94a3b8;line-height:1.5;"></ul>
    </div>
  </div>
<script>
async function refreshState() {
  try {
    const r = await fetch('/api/state');
    const d = await r.json();
    document.getElementById('my-slot').innerText = d.status.my_slot;
    document.getElementById('sync-info').innerText =
      `Pick #${d.status.overall_pick} (Tur ${d.status.round}.${d.status.pick_in_round}) | Son Senkron: ${d.status.last_sync_source} (${d.status.last_sync_time || 'Hazır'})`;
    const tb = document.getElementById('turn-badge');
    if (d.status.is_my_turn) {
      tb.className = 'badge badge-turn';
      tb.innerText = `⚡ SIRA SENDE! (SLOT #${d.status.my_slot})`;
    } else {
      tb.className = 'badge badge-wait';
      tb.innerText = `Sıradaki: Slot #${d.status.on_clock_slot} (${d.status.picks_until_mine} seçim sonra sen)`;
    }
    document.getElementById('calc-speed').innerText = `Hesaplama: ${d.elapsed_ms ? d.elapsed_ms.toFixed(0) : 0} ms`;
    const tbody = document.getElementById('rec-tbody');
    tbody.innerHTML = d.recommendations.map((rec, i) => `
      <tr>
        <td><b>#${i+1}</b></td>
        <td><b>${rec.NAME}</b></td>
        <td>${rec.TEAM} - ${rec.POS}</td>
        <td class="win-score">${rec.WIN_PROB_SCORE.toFixed(3)}</td>
        <td>${rec.FAST_SCORE >= 0 ? '+' : ''}${rec.FAST_SCORE.toFixed(2)}</td>
        <td>${rec.BASE_Z.toFixed(2)}</td>
        <td>${rec.Active_Punts}</td>
        <td><button class="btn" onclick="pickById(${rec.ID})">Seç</button></td>
      </tr>
    `).join('');
    document.getElementById('roster-count').innerText = d.my_roster.length;
    document.getElementById('my-roster-list').innerHTML = d.my_roster.map(p => `<li><b>${p.name}</b> (${p.team} - ${p.pos})</li>`).join('');
    document.getElementById('cat-probs').innerHTML = Object.entries(d.category_win_probs || {})
      .map(([k,v]) => `<span style="display:inline-block;margin-right:8px;padding:2px 6px;border-radius:4px;background:${v>=0.52?'#064e3b':(v<0.38?'#450a0a':'#1e293b')}"><b>${k}:</b> %${(v*100).toFixed(0)}</span>`).join('');
    document.getElementById('recent-picks').innerHTML = (d.recent_picks || []).map(p =>
      `<li>Pick #${p.overall}: <b>${p.name}</b> (Slot #${p.slot}${p.is_mine ? ' - BİZ' : ''})</li>`).join('');
  } catch (e) {}
}
async function pickById(pid) {
  await fetch('/api/manual_pick', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query: String(pid), is_mine: false})});
  refreshState();
}
async function submitManualPick(isMine) {
  const q = document.getElementById('manual-input').value.trim();
  if (!q) return;
  await fetch('/api/manual_pick', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query: q, is_mine: isMine})});
  document.getElementById('manual-input').value = '';
  refreshState();
}
async function undoPick() {
  await fetch('/api/undo', {method:'POST'});
  refreshState();
}
setInterval(refreshState, 1200);
refreshState();
</script>
</body>
</html>
"""


class YahooLiveDraftBridgeManager:
    """
    Runs two non-blocking background daemon threads alongside the manual CLI (`interactive_loop`):
      1. Local HTTP Bridge Server (`http://127.0.0.1:8765`) receiving zero-latency picks from
         `yahoo_draft_bridge.user.js` in the browser and serving instant AI recommendations.
      2. Optional Yahoo OAuth2 API Poller (`YahooFantasyOAuthClient`) polling `/draftresults`
         every 2.0 seconds with automatic token refresh.
    """

    def __init__(self, assistant, host="127.0.0.1", port=8765, poll_interval_sec=2.0):
        self.assistant = assistant
        self.host = host
        self.port = port
        self.poll_interval_sec = poll_interval_sec
        self.oauth_client = YahooFantasyOAuthClient()
        self.running = False
        self.http_server = None
        self.last_notified_pick_count = 0

    def build_state_payload(self, fast_only=False):
        st = self.assistant.get_draft_status()
        t0 = time.perf_counter()
        if fast_only:
            df_sug = self.assistant.get_fast_suggestions(top_n=8)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            recs = []
            for _, row in df_sug.iterrows():
                recs.append({
                    'ID': int(row['ID']),
                    'NAME': str(row['NAME']),
                    'TEAM': str(row.get('TEAM', 'NBA')),
                    'POS': str(row['POS']),
                    'WIN_PROB_SCORE': float(row.get('FAST_SCORE', 0.0)),
                    'FAST_SCORE': float(row.get('FAST_SCORE', 0.0)),
                    'BASE_Z': float(row.get('BASE_Z', 0.0)),
                    'Active_Punts': str(row.get('Active_Punts', 'Dengeli')),
                })
        else:
            df_sug = self.assistant.rank_available_players(
                enable_logging=False, timeout_budget_sec=2.2, use_cache=True
            )
            elapsed_ms = float(df_sug.attrs.get('elapsed_ms', (time.perf_counter() - t0) * 1000.0))
            recs = []
            for _, row in df_sug.head(8).iterrows():
                recs.append({
                    'ID': int(row['ID']),
                    'NAME': str(row['NAME']),
                    'TEAM': str(row.get('TEAM', 'NBA')),
                    'POS': str(row['POS']),
                    'WIN_PROB_SCORE': float(row['WIN_PROB_SCORE']),
                    'FAST_SCORE': float(row['FAST_SCORE']),
                    'BASE_Z': float(row['BASE_Z']),
                    'Active_Punts': str(row['Active_Punts']),
                    'Predicted_Picks': str(row.get('Predicted_Picks', '')),
                })

        with self.assistant.lock:
            my_roster_info = []
            for pid in self.assistant.my_roster:
                my_roster_info.append({
                    'id': int(pid),
                    'name': self.assistant.players[pid].name if pid in self.assistant.players else str(pid),
                    'team': self.assistant.team_abbr_dict.get(pid, 'NBA'),
                    'pos': self.assistant.pos_dict.get(pid, 'UTIL'),
                })
            _, cat_win_probs = self.assistant._compute_marginal_category_weights(self.assistant.my_roster)

            recent_picks = []
            total_hist = len(self.assistant.pick_history)
            for idx_h in range(max(0, total_hist - 8), total_hist):
                pid, t_idx, is_mine = self.assistant.pick_history[idx_h]
                recent_picks.append({
                    'overall': idx_h + 1,
                    'id': int(pid),
                    'name': self.assistant.players[pid].name if pid in self.assistant.players else str(pid),
                    'slot': t_idx + 1,
                    'is_mine': bool(is_mine),
                })
            recent_picks.reverse()

        return {
            'status': st,
            'elapsed_ms': elapsed_ms,
            'recommendations': recs,
            'my_roster': my_roster_info,
            'category_win_probs': {k: round(float(v), 3) for k, v in cat_win_probs.items()},
            'recent_picks': recent_picks,
            'oauth_configured': self.oauth_client.is_configured(),
            'oauth_last_error': self.oauth_client.last_error,
        }

    def notify_console_on_new_picks(self, applied_events):
        if not applied_events:
            return
        for overall_num, pid, p_name, t_idx, is_mine in applied_events:
            tag = ">>> BİZİM SEÇİMİMİZ <<<" if is_mine else f"Slot #{t_idx + 1}"
            print(f"\n🔄 [YAHOO CANLI SENKRON] Pick #{overall_num}: {p_name} ({tag})")

        st = self.assistant.get_draft_status()
        if st['is_my_turn']:
            df_sug = self.assistant.rank_available_players(enable_logging=False, timeout_budget_sec=2.2, use_cache=True)
            elapsed_ms = df_sug.attrs.get('elapsed_ms', 0.0)
            print(f"\n⚡ >>> SIRA SENDE (SLOT #{st['my_slot']} | Tur {st['round']})! [Hesaplama: {elapsed_ms:.0f} ms] <<<")
            cols = ['ID', 'NAME', 'TEAM', 'POS', 'WIN_PROB_SCORE', 'FAST_SCORE', 'BASE_Z', 'Active_Punts']
            print(df_sug[cols].head(6).to_string(index=False))
            print("\nDraft> ", end="", flush=True)
        else:
            print(f"[Sıradaki: Slot #{st['on_clock_slot']} | {st['picks_until_mine']} seçim sonra sen]\nDraft> ", end="", flush=True)

    def _start_http_server(self):
        manager = self

        class BridgeHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Keep CLI prompt clean

            def _send_json(self, data, status=200):
                raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Access-Control-Request-Private-Network')
                self.send_header('Access-Control-Allow-Private-Network', 'true')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Access-Control-Request-Private-Network')
                self.send_header('Access-Control-Allow-Private-Network', 'true')
                self.send_header('Content-Length', '0')
                self.end_headers()

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path in ('/', '/dashboard'):
                    raw = DASHBOARD_HTML.encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Private-Network', 'true')
                    self.send_header('Content-Length', str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return
                if parsed.path in ('/bridge.js', '/userscript.js'):
                    script_path = os.path.join(PROJECT_ROOT, 'src', 'yahoo_draft_bridge.user.js')
                    if os.path.exists(script_path):
                        with open(script_path, 'r', encoding='utf-8') as f:
                            raw = f.read().encode('utf-8')
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/javascript; charset=utf-8')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Private-Network', 'true')
                        self.send_header('Content-Length', str(len(raw)))
                        self.end_headers()
                        self.wfile.write(raw)
                        return
                if parsed.path in ('/api/state', '/api/recommendations'):
                    qs = urllib.parse.parse_qs(parsed.query)
                    fast_only = qs.get('mode', [''])[0] == 'fast'
                    payload = manager.build_state_payload(fast_only=fast_only)
                    self._send_json(payload)
                    return
                if parsed.path == '/api/injuries':
                    tracker = getattr(manager.assistant, 'injury_tracker', None)
                    injuries = tracker.get_all_active_injuries() if tracker else []
                    self._send_json({'ok': True, 'injuries': injuries})
                    return
                self._send_json({'error': 'Not found'}, status=404)

            def do_POST(self):
                parsed = urllib.parse.urlparse(self.path)
                length = int(self.headers.get('Content-Length', 0))
                body_raw = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
                try:
                    body = json.loads(body_raw)
                except Exception:
                    body = {}

                if parsed.path == '/api/sync_picks':
                    picks = body.get('picks', [])
                    my_slot = body.get('my_slot')
                    if isinstance(my_slot, int) and 1 <= my_slot <= manager.assistant.num_teams and not manager.assistant.pick_history:
                        manager.assistant.my_team_idx = my_slot - 1
                    applied = manager.assistant.sync_external_picks(picks, source="browser_bridge")
                    if applied:
                        manager.notify_console_on_new_picks(applied)
                    payload = manager.build_state_payload(fast_only=False)
                    payload['newly_applied'] = len(applied)
                    self._send_json(payload)
                    return

                if parsed.path == '/api/manual_pick':
                    query = str(body.get('query', '')).strip()
                    is_mine = bool(body.get('is_mine', False))
                    pid = manager.assistant.resolve_player_id(query, only_available=True)
                    if pid is None:
                        self._send_json({'ok': False, 'error': f"Oyuncu bulunamadı: {query}"}, status=400)
                        return
                    if is_mine:
                        manager.assistant.draft_player(pid, source="web_manual")
                    else:
                        manager.assistant.pick_player(pid, source="web_manual")
                    self._send_json({'ok': True, 'state': manager.build_state_payload(fast_only=False)})
                    return

                if parsed.path == '/api/undo':
                    manager.assistant.undo_last_pick()
                    self._send_json({'ok': True, 'state': manager.build_state_payload(fast_only=False)})
                    return

                if parsed.path == '/api/injuries/update':
                    player_query = str(body.get('player', '')).strip()
                    status = str(body.get('status', 'OUT')).upper().strip()
                    desc = str(body.get('desc', ''))
                    is_b2b = bool(body.get('is_b2b_rest', False))
                    tracker = getattr(manager.assistant, 'injury_tracker', None)
                    pid = manager.assistant.resolve_player_id(player_query, only_available=False)
                    if pid is None or tracker is None:
                        self._send_json({'ok': False, 'error': f"Oyuncu bulunamadı: {player_query}"}, status=400)
                        return
                    p_name = manager.assistant.players[pid].name if pid in manager.assistant.players else player_query
                    team_name = manager.assistant.team_abbr_dict.get(pid, 'NBA')
                    if status in ('HEALTHY', 'CLEAR', 'ACT'):
                        tracker.clear_injury(pid)
                        if pid in manager.assistant.players:
                            manager.assistant.players[pid].update_injury_status('HEALTHY')
                    else:
                        tracker.set_injury(pid, p_name, status, team=team_name, desc=desc, is_b2b_rest=is_b2b, source="api")
                        if pid in manager.assistant.players:
                            manager.assistant.players[pid].update_injury_status(status, desc, is_b2b_rest=is_b2b)
                    self._send_json({'ok': True, 'player_id': pid, 'name': p_name, 'status': status})
                    return

                if parsed.path == '/api/sync_injuries':
                    records = body.get('injuries', [])
                    tracker = getattr(manager.assistant, 'injury_tracker', None)
                    if not tracker:
                        self._send_json({'ok': False, 'error': "InjuryTracker aktif değil"}, status=500)
                        return
                    updated_cnt = tracker.bulk_sync_yahoo_statuses(
                        records,
                        lambda q: manager.assistant.resolve_player_id(q, only_available=False)
                    )
                    manager.assistant._sync_injuries_into_players()
                    self._send_json({'ok': True, 'updated': updated_cnt})
                    return

                self._send_json({'error': 'Unknown endpoint'}, status=404)

        try:
            self.http_server = ThreadingHTTPServer((self.host, self.port), BridgeHandler)
            self.http_server.serve_forever()
        except Exception as e:
            print(f"[UYARI] Yerel HTTP Köprü Sunucusu ({self.host}:{self.port}) başlatılamadı: {e}")

    def _poll_yahoo_oauth_loop(self):
        while self.running:
            try:
                if self.oauth_client.is_configured():
                    api_picks = self.oauth_client.fetch_live_draft_picks()
                    if api_picks:
                        applied = self.assistant.sync_external_picks(api_picks, source="yahoo_oauth_api")
                        if applied:
                            self.notify_console_on_new_picks(applied)
            except Exception as e:
                self.oauth_client.last_error = str(e)
            time.sleep(self.poll_interval_sec)

    def start_background_services(self):
        if self.running:
            return
        self.running = True
        t_http = threading.Thread(target=self._start_http_server, daemon=True)
        t_http.start()
        t_poll = threading.Thread(target=self._poll_yahoo_oauth_loop, daemon=True)
        t_poll.start()
        # Pre-warm Round 1 suggestions immediately in the background so Pick #8 is 0ms cached
        self.assistant.precompute_suggestions_async()
