"""
Yahoo Fantasy 1-Click Browser Bookmarklet & Local Sync Bridge (`127.0.0.1:8765`).

Zero-Cookie, Zero-Password, Zero-OAuth-Approval Solution:
  - Runs inside your logged-in Yahoo Fantasy browser tab via a 1-click Bookmarklet.
  - Automatically fetches in parallel (same-origin inside the browser):
      1. All 14 Teams' Live Rosters & IL/IL+ Slots (`/nba/64691/1` .. `/nba/64691/14`)
         -> Reconstructs the exact league-wide Free Agent pool after all 14 managers' add/drops.
      2. Recent League Transactions (`/nba/64691/transactions`)
         -> Tracks who added/dropped whom across all 14 teams.
      3. Live H2H Matchup Scoreboard & Remaining Games (`/nba/64691/matchup`)
         -> Captures `FGM/A, FG%, FTM/A, FT%, 3PTM, PTS, REB, AST, ST, BLK, TO` and `Played / Remaining Games`.
  - Posts the clean JSON to `http://127.0.0.1:8765/sync_league`, which updates
    `data/processed/league_state.json` and `data/processed/live_matchup.json` and immediately
    triggers `run_cloud_sync()` (including the Telegram comparative scoreboard notification).
"""
import os
import sys
import json
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SRC_DIR)

from src import draft_data
from src.cloud_sync import run_cloud_sync


# The client-side JavaScript executed inside the Yahoo Fantasy tab when the Bookmarklet is clicked.
BOOKMARKLET_JS_RAW = r"""
(async function(){
  const banner = document.createElement('div');
  banner.style.cssText = 'position:fixed;top:14px;right:14px;z-index:999999;background:#065f46;color:#fff;padding:14px 20px;border-radius:10px;font:600 14px system-ui,sans-serif;box-shadow:0 10px 25px rgba(0,0,0,0.45);border:1px solid #34d399;max-width:440px;';
  banner.textContent = '🏀 NBA Fantasy: 14 Takım Kadrosu, Boştaki Oyuncular ve Canlı Matchup Taranıyor...';
  document.body.appendChild(banner);

  try {
    const mPath = location.pathname.match(/\/nba\/(\d+)/);
    const leagueId = mPath ? mPath[1] : '64691';
    const parser = new DOMParser();

    function parseRosterDoc(doc, slotNum) {
      const players = [];
      const ilList = [];
      const unslottedInj = [];
      const seen = new Set();
      let teamName = '';
      const titleEl = doc.querySelector('title');
      if (titleEl && titleEl.textContent.includes('-')) {
        teamName = titleEl.textContent.split('-')[0].replace(/Yahoo Fantasy.*/i, '').trim();
      }
      const h1El = doc.querySelector('#team-card h1, .TeamName, .Navitem-main, h1');
      if (!teamName && h1El) teamName = h1El.textContent.trim();

      const links = doc.querySelectorAll('a[href*="/nba/players/"]');
      links.forEach(a => {
        const name = (a.textContent || '').trim();
        if (!name || name.length < 3 || seen.has(name) || /^(View|Note|Player|Stats|Video)$/i.test(name) || /player\s*note/i.test(name)) return;
        const tr = a.closest('tr');
        if (!tr) return;
        seen.add(name);

        let selPos = 'BN';
        const posEl = tr.querySelector('td.pos, span.pos-label, [data-pos], td:first-child');
        if (posEl) {
          const rawPos = (posEl.getAttribute('data-pos') || posEl.textContent || '').trim().toUpperCase();
          if (/^(PG|SG|G|SF|PF|F|C|UTIL|BN|IL\+?|IR\+?)$/.test(rawPos)) {
            selPos = rawPos.replace('IR', 'IL');
          }
        }

        let status = 'HEALTHY';
        const injEl = tr.querySelector('abbr.F-injury, span.F-injury, .ysf-player-status span');
        if (injEl) {
          const stTxt = (injEl.textContent || '').trim().toUpperCase();
          if (/^(INJ|O|OUT|IL|GTD|DTD|SUSP)$/.test(stTxt)) status = stTxt;
        }

        players.push({ name, selected_position: selPos, status });
        if (selPos === 'IL' || selPos === 'IL+') {
          ilList.push(name);
        } else if (['INJ', 'O', 'OUT', 'IL', 'GTD', 'DTD'].includes(status)) {
          unslottedInj.push({ name, status, slot: selPos });
        }
      });
      return { slotIdx: slotNum - 1, teamName, players, ilList, unslottedInj };
    }

    function parseMatchupDoc(doc) {
      const bodyTxt = (doc.body && doc.body.innerText) ? doc.body.innerText : '';
      let remA = null, gpA = null, totA = null, gpB = null, totB = null, remB = null;
      const mGames = bodyTxt.match(/(\d+)\s*Remaining[\s\S]{0,180}?(\d+)\s*\/\s*(\d+)\s*Games\s*Played\s*(\d+)\s*\/\s*(\d+)[\s\S]{0,180}?Remaining\s*(\d+)/i);
      if (mGames) {
        remA = parseInt(mGames[1], 10);
        gpA  = parseInt(mGames[2], 10);
        totA = parseInt(mGames[3], 10);
        gpB  = parseInt(mGames[4], 10);
        totB = parseInt(mGames[5], 10);
        remB = parseInt(mGames[6], 10);
      }

      const tables = Array.from(doc.querySelectorAll('table'));
      for (const tbl of tables) {
        const ths = Array.from(tbl.querySelectorAll('thead th, tr:first-child th')).map(x => (x.textContent || '').trim().toUpperCase());
        if (ths.includes('PTS') && ths.includes('REB') && ths.includes('AST')) {
          const rows = Array.from(tbl.querySelectorAll('tbody tr')).filter(r => r.querySelectorAll('td, th').length >= 9);
          if (rows.length >= 2) {
            const parseRow = (tr, isFirst) => {
              const cells = Array.from(tr.querySelectorAll('th, td')).map(c => (c.textContent || '').trim());
              const obj = {
                name: cells.find(c => c.length > 2 && !/^\d/.test(c)) || (isFirst ? "Berk's Best Team" : "SILE BULLS"),
                slot: isFirst ? 8 : 13,
                games_played: (isFirst ? gpA : gpB) ?? 30,
                games_remaining: (isFirst ? remA : remB) ?? 7,
                total_scheduled: (isFirst ? totA : totB) ?? 37
              };
              const tLink = tr.querySelector('a[href*="/nba/' + leagueId + '/"]');
              if (tLink && tLink.textContent.trim()) {
                obj.name = tLink.textContent.trim();
              }
              // Anchor on first fraction cell (`FGM/FGA`, e.g. `145/316`) so colspan never shifts columns!
              const idxFgm = cells.findIndex(c => /^\d+\s*\/\s*\d+$/.test(c));
              if (idxFgm >= 0 && cells.length >= idxFgm + 11) {
                const pFg = cells[idxFgm].split('/');
                obj.FGM = parseFloat(pFg[0]) || 0;
                obj.FGA = parseFloat(pFg[1]) || 0;
                const pFt = (cells[idxFgm + 2] || '0/0').split('/');
                obj.FTM = parseFloat(pFt[0]) || 0;
                obj.FTA = parseFloat(pFt[1]) || 0;
                obj.FG3M = parseFloat(cells[idxFgm + 4]) || 0;
                obj.PTS  = parseFloat(cells[idxFgm + 5]) || 0;
                obj.REB  = parseFloat(cells[idxFgm + 6]) || 0;
                obj.AST  = parseFloat(cells[idxFgm + 7]) || 0;
                obj.STL  = parseFloat(cells[idxFgm + 8]) || 0;
                obj.BLK  = parseFloat(cells[idxFgm + 9]) || 0;
                obj.TOV  = parseFloat(cells[idxFgm + 10]) || 0;
              }
              return obj;
            };
            let tA = parseRow(rows[0], true);
            let tB = parseRow(rows[1], false);
            if (!tA.name.toLowerCase().includes('berk') && tB.name.toLowerCase().includes('berk')) {
              const tmp = tA; tA = tB; tB = tmp;
            }
            tA.slot = 8;
            tB.slot = 13;
            return { team_a: tA, team_b: tB };
          }
        }
      }
      return null;
    }

    function parseTransactionsDoc(doc) {
      const txs = [];
      const rows = Array.from(doc.querySelectorAll('table tbody tr'));
      rows.forEach((tr, idx) => {
        const pLinks = Array.from(tr.querySelectorAll('a[href*="/nba/players/"]'));
        if (!pLinks.length) return;
        const tLink = tr.querySelector('a[href*="/nba/' + leagueId + '/"]');
        const teamName = tLink ? tLink.textContent.trim() : 'League';
        const added = [], dropped = [];
        pLinks.forEach((pl, pIdx) => {
          const pName = pl.textContent.trim();
          const containerTxt = (pl.parentElement ? pl.parentElement.textContent : tr.textContent).toLowerCase();
          if (pIdx === 0 && (pLinks.length > 1 || !containerTxt.includes('drop'))) {
            added.push({ player_name: pName, team_name: teamName });
          } else {
            dropped.push({ player_name: pName, team_name: teamName });
          }
        });
        if (added.length || dropped.length) {
          txs.push({ transaction_id: 'dom_' + idx, type: 'add/drop', timestamp: Math.floor(Date.now()/1000) - idx, added, dropped });
        }
      });
      return txs.slice(0, 20);
    }

    // 1. Check current page for matchup first
    let matchup = parseMatchupDoc(document);

    // 2. Fetch all 14 teams' live rosters in parallel
    banner.textContent = '🏀 (1/3) 14 Takımın Canlı Kadroları & IL+ Yuvaları Çekiliyor...';
    const slotNums = Array.from({length: 14}, (_, i) => i + 1);
    const teamHtmls = await Promise.all(slotNums.map(s =>
      fetch(`/nba/${leagueId}/${s}`, { credentials: 'same-origin' }).then(r => r.ok ? r.text() : '').catch(() => '')
    ));

    const rostersBySlot = {};
    const teamNamesBySlot = {};
    const ilBySlot = {};
    const unslottedBySlot = {};
    const emptyBySlot = {};

    teamHtmls.forEach((html, i) => {
      if (!html) return;
      const doc = parser.parseFromString(html, 'text/html');
      const parsed = parseRosterDoc(doc, i + 1);
      if (parsed.players.length > 0) {
        rostersBySlot[parsed.slotIdx] = parsed.players;
        teamNamesBySlot[parsed.slotIdx] = parsed.teamName;
        ilBySlot[parsed.slotIdx] = parsed.ilList;
        unslottedBySlot[parsed.slotIdx] = parsed.unslottedInj;
        const nonIl = parsed.players.filter(p => p.selected_position !== 'IL' && p.selected_position !== 'IL+').length;
        emptyBySlot[parsed.slotIdx] = Math.max(0, 13 - nonIl);
      }
    });

    // 3. Fetch Matchup & Transactions pages if needed
    banner.textContent = '🏀 (2/3) Canlı Skor Tablosu ve Son Add/Drop İşlemleri Çekiliyor...';
    if (!matchup) {
      for (const mUrl of [`/nba/${leagueId}/matchup`, `/nba/${leagueId}`]) {
        const mHtml = await fetch(mUrl, { credentials: 'same-origin' }).then(r => r.ok ? r.text() : '').catch(() => '');
        if (mHtml) {
          matchup = parseMatchupDoc(parser.parseFromString(mHtml, 'text/html'));
          if (matchup) break;
        }
      }
    }

    let transactions = [];
    const txHtml = await fetch(`/nba/${leagueId}/transactions`, { credentials: 'same-origin' }).then(r => r.ok ? r.text() : '').catch(() => '');
    if (txHtml) {
      transactions = parseTransactionsDoc(parser.parseFromString(txHtml, 'text/html'));
    }

    // 4. Send to local bridge (`http://127.0.0.1:8765/sync_league`)
    banner.textContent = '🏀 (3/3) Python Motoruna Gönderiliyor & Telegram Bildirimi Hazırlanıyor...';
    const payload = {
      league_id: leagueId,
      rosters_by_slot: rostersBySlot,
      team_names_by_slot: teamNamesBySlot,
      il_players_by_slot: ilBySlot,
      unslotted_injured_by_slot: unslottedBySlot,
      empty_active_slots_by_slot: emptyBySlot,
      transactions: transactions,
      matchup: matchup
    };

    const resp = await fetch('http://127.0.0.1:8765/sync_league', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const resJson = await resp.json();
    banner.style.background = '#047857';
    banner.textContent = `✅ Senkron Tamamlandı! (${resJson.teams_synced} Takım Kadrosu, ${resJson.total_players} Oyuncu). Telegram Bildirimi Gönderildi!`;
    setTimeout(() => banner.remove(), 7000);
  } catch (err) {
    banner.style.background = '#b91c1c';
    banner.textContent = '❌ Hata: ' + err.message + ' (Terminalin açık olduğundan emin olun: python src/yahoo_browser_sync.py)';
    setTimeout(() => banner.remove(), 9000);
  }
})();
""".strip()


def _resolve_canonical_draft_slot(player_names, fallback_slot):
    """
    Maps a fetched Yahoo team roster (indexed by Yahoo registration order 1..14)
    to its canonical slot 0..13 in `draft_data.TEAM_NAMES` by matching against
    initial drafted rosters (`DRAFT_PICKS_BY_ROUND`).
    """
    from src.injury_tracker import normalize_name
    norm_roster = {normalize_name(n) for n in player_names if n}
    best_slot = int(fallback_slot)
    best_overlap = -1
    for slot_idx in range(draft_data.NUM_TEAMS):
        drafted_for_slot = set()
        for rnd, picks in draft_data.DRAFT_PICKS_BY_ROUND.items():
            idx = slot_idx if (rnd % 2 == 1) else (draft_data.NUM_TEAMS - 1 - slot_idx)
            if 0 <= idx < len(picks):
                drafted_for_slot.add(normalize_name(picks[idx]))
        overlap = len(norm_roster & drafted_for_slot)
        if overlap > best_overlap:
            best_overlap = overlap
            best_slot = slot_idx
    return str(best_slot)


def apply_browser_sync_payload(payload, run_async_cloud=True):
    """
    Processes the JSON payload received from the Browser Bookmarklet:
      1. Maps each of the 14 Yahoo rosters to its canonical slot (`0..13`) in `draft_data.TEAM_NAMES`
         and updates `data/processed/league_state.json` (with `"live_synced": True`).
      2. Updates `data/processed/live_matchup.json` if live matchup stats (`FGM/A`, `PTS`, etc.) are present.
      3. Pushes updated JSON state to GitHub and triggers `run_cloud_sync()` asynchronously so the
         browser receives an immediate `<1s` confirmation banner.
    """
    import threading
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    rosters_by_slot = payload.get("rosters_by_slot", {})
    raw_il = payload.get("il_players_by_slot", {})
    raw_unslotted = payload.get("unslotted_injured_by_slot", {})
    raw_empty = payload.get("empty_active_slots_by_slot", {})

    rosters_clean = {}
    il_clean = {}
    unslotted_clean = {}
    empty_clean = {}
    total_players = 0

    for s_key, p_list in rosters_by_slot.items():
        names = [
            str(p.get("name", "")).strip()
            for p in p_list
            if isinstance(p, dict) and p.get("name") and "player note" not in str(p.get("name", "")).lower()
        ]
        if names:
            canon_key = _resolve_canonical_draft_slot(names, s_key)
            rosters_clean[canon_key] = names
            total_players += len(names)
            il_clean[canon_key] = [
                n for n in raw_il.get(s_key, raw_il.get(str(s_key), []))
                if "player note" not in str(n).lower()
            ]
            unslotted_clean[canon_key] = [
                it for it in raw_unslotted.get(s_key, raw_unslotted.get(str(s_key), []))
                if isinstance(it, dict) and "player note" not in str(it.get("name", "")).lower()
            ]
            empty_clean[canon_key] = int(raw_empty.get(s_key, raw_empty.get(str(s_key), 0)))

    # Save live_matchup.json only if valid FGM/FGA & PTS stats are present
    matchup_obj = payload.get("matchup")
    has_valid_matchup = (
        isinstance(matchup_obj, dict)
        and isinstance(matchup_obj.get("team_a"), dict)
        and isinstance(matchup_obj.get("team_b"), dict)
        and "FGM" in matchup_obj["team_a"]
        and "PTS" in matchup_obj["team_a"]
    )
    if has_valid_matchup:
        live_matchup_path = os.path.join(PROCESSED_DIR, "live_matchup.json")
        with open(live_matchup_path, "w", encoding="utf-8") as f:
            json.dump({
                "week": int(payload.get("week", 1)),
                "updated_at": now_iso,
                "matchup": matchup_obj,
            }, f, indent=2)

    # Save league_state.json with `live_synced: True` so `run_cloud_sync()` loads the 14 live rosters
    state_json_path = os.path.join(PROCESSED_DIR, "league_state.json")
    prior_state = {}
    if os.path.exists(state_json_path):
        try:
            with open(state_json_path, "r", encoding="utf-8") as f:
                prior_state = json.load(f)
        except Exception:
            prior_state = {}

    merged_rosters = prior_state.get("rosters", {})
    merged_rosters.update(rosters_clean)

    # Clean empty dropped entries in transactions
    raw_txs = payload.get("transactions", prior_state.get("transactions", []))[:25]
    clean_txs = []
    for tx in raw_txs:
        if not isinstance(tx, dict):
            continue
        adds = [a for a in tx.get("added", []) if isinstance(a, dict) and a.get("player_name", "").strip()]
        drops = [d for d in tx.get("dropped", []) if isinstance(d, dict) and d.get("player_name", "").strip()]
        if adds or drops:
            clean_txs.append({
                "transaction_id": tx.get("transaction_id", ""),
                "type": tx.get("type", "add/drop"),
                "timestamp": tx.get("timestamp", 0),
                "added": adds,
                "dropped": drops,
            })

    berk_slot_str = str(draft_data.MY_TEAM_IDX)
    state_data = {
        "updated_at": now_iso,
        "league_id": str(payload.get("league_id", "64691")),
        "league_key": f"nba.l.{payload.get('league_id', '64691')}",
        "live_synced": True,
        "sync_status": f"Tarayıcı Köprüsü Aktif ({len(merged_rosters)} Takım Canlı Kadro & Skor)",
        "rosters": merged_rosters,
        "berk_roster_names": merged_rosters.get(berk_slot_str, []),
        "il_slots": il_clean or prior_state.get("il_slots", {}),
        "unslotted_injured": unslotted_clean or prior_state.get("unslotted_injured", {}),
        "empty_active_slots": empty_clean or prior_state.get("empty_active_slots", {}),
        "transactions": clean_txs,
    }
    with open(state_json_path, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=2)

    def _bg_sync_and_push():
        try:
            run_cloud_sync()
        except Exception as e:
            print(f"[WARN] Cloud sync error: {e}")
        try:
            import subprocess
            subprocess.run(
                ["git", "add", "-f", "data/processed/league_state.json", "data/processed/live_matchup.json"],
                cwd=PROJECT_ROOT, check=False, capture_output=True, timeout=10
            )
            commit_res = subprocess.run(
                ["git", "commit", "-m", "🔄 [Browser Bridge] Sync live 14-team Yahoo rosters, FA pool & matchup"],
                cwd=PROJECT_ROOT, check=False, capture_output=True, timeout=10
            )
            if commit_res.returncode == 0:
                subprocess.run(
                    ["git", "push"],
                    cwd=PROJECT_ROOT, check=False, capture_output=True, timeout=25
                )
                print("  [GIT] Guncel 14 takim kadrosu ve canli skor GitHub'a pushlandi (GitHub Actions tetiklendi)!")
        except Exception as e:
            print(f"[WARN] Git push error: {e}")

    if run_async_cloud:
        threading.Thread(target=_bg_sync_and_push, daemon=True).start()
    else:
        _bg_sync_and_push()

    return {
        "ok": True,
        "teams_synced": len(rosters_clean),
        "total_players": total_players,
        "matchup_synced": has_valid_matchup,
    }


def build_setup_html():
    import urllib.parse
    minified_js = " ".join(line.strip() for line in BOOKMARKLET_JS_RAW.splitlines() if not line.strip().startswith("//"))
    bookmarklet_href = "javascript:" + urllib.parse.quote(minified_js)
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<title>🏀 Yahoo Fantasy 1-Tıkla Canlı Senkronizasyon Köprüsü</title>
<style>
  body {{ background:#0b0f19; color:#e2e8f0; font-family:'Segoe UI',system-ui,sans-serif; max-width:820px; margin:36px auto; padding:24px; line-height:1.6; }}
  .card {{ background:#111827; border:1px solid #1f2937; border-radius:12px; padding:24px; margin-bottom:20px; }}
  h1 {{ margin-top:0; color:#f8fafc; font-size:22px; }}
  .bm-btn {{ display:inline-block; background:#059669; color:#fff; text-decoration:none; font-weight:700; font-size:16px; padding:14px 24px; border-radius:8px; border:2px dashed #6ee7b7; cursor:grab; margin:12px 0; }}
  .bm-btn:hover {{ background:#047857; }}
  code, pre {{ background:#0f172a; color:#38bdf8; padding:10px; border-radius:6px; overflow-x:auto; display:block; font-size:12px; }}
  .copy-btn {{ background:#2563eb; color:#fff; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:600; margin-top:8px; }}
</style>
</head>
<body>
  <div class="card">
    <h1>🏀 Yahoo Fantasy 1-Tıkla Senkronizasyon (Sıfır Cookie / Sıfır OAuth İzni)</h1>
    <p>Yahoo API başvurunuz onaylanana kadar <b>14 takımın tamamının güncel kadrolarını</b>, <b>boştaki (FA) oyuncuları</b>, <b>IL+ yuvalarını</b> ve <b>canlı Matchup skor tablosunu</b> tek tıkla çekmek için:</p>
    <ol>
      <li>Aşağıdaki yeşil butonu fareyle tutup tarayıcınızın <b>Yer İmleri Çubuğuna (Bookmarks Bar)</b> sürükleyip bırakın:</li>
    </ol>
    <p><a class="bm-btn" href="{bookmarklet_href}">🏀 NBA Fantasy Sync</a></p>
    <ol start="2">
      <li>Tarayıcınızda <b>Yahoo Fantasy Matchup</b> sayfanızı açın ve yer imi çubuğundaki <b>🏀 NBA Fantasy Sync</b> butonuna tıklayın!</li>
      <li>Yaklaşık 2 saniye içinde 14 takımın kadrosu, boştaki FA havuzu ve canlı skorlar çekilip <b>Telegram</b>'a güncel tablo olarak gönderilecektir.</li>
    </ol>
  </div>
  <div class="card">
    <h3>Alternatif: Tarayıcı Konsolundan (F12 -> Console) Çalıştırma Kodu</h3>
    <pre id="rawJs">{BOOKMARKLET_JS_RAW}</pre>
    <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('rawJs').innerText);this.innerText='✅ Kopyalandı!';">📋 Konsol Kodunu Kopyala</button>
  </div>
</body>
</html>"""


class BrowserSyncHandler(BaseHTTPRequestHandler):
    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        html = build_setup_html().encode("utf-8")
        self.send_response(200)
        self._send_cors()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html)

    def do_POST(self):
        if self.path.startswith("/sync_league"):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                payload = json.loads(raw)
                res = apply_browser_sync_payload(payload)
                out = json.dumps(res).encode("utf-8")
                self.send_response(200)
                self._send_cors()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(out)
            except Exception as e:
                err = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
                self.send_response(500)
                self._send_cors()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(err)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def run_browser_sync_server(port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), BrowserSyncHandler)
    url = f"http://127.0.0.1:{port}/"
    print("=" * 78)
    print(f"🏀 YAHOO FANTASY 1-TIKLA TARAYICI SENKRON KÖPRÜSÜ AKTİF: {url}")
    print("=" * 78)
    print("1. Tarayıcınızda otomatik açılan sayfadan '🏀 NBA Fantasy Sync' butonunu Yer İmlerinize sürükleyin.")
    print("2. Yahoo Fantasy sayfanızdayken o yer imine tıklayın.")
    print("3. 14 takımın güncel kadroları, FA havuzu ve canlı skorlar anında senkronize edilip Telegram'a düşecektir!")
    print("(Durdurmak için Ctrl+C)\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[BİLGİ] Köprü kapatıldı.")


if __name__ == "__main__":
    run_browser_sync_server()
