// ==UserScript==
// @name         🏀 Antigravity Yahoo NBA Fantasy Live Draft Bridge & HUD (14-Takım, Slot #8)
// @namespace    http://127.0.0.1:8765/
// @version      5.1.0
// @description  Yahoo Canlı Draft odasındaki Board (Tam İsim) ve Sol Picks listesini sıfır hatayla yakalar, menajer adlarını ve Players tablosunu filtreler.
// @match        https://basketball.fantasysports.yahoo.com/*
// @match        https://*.fantasysports.yahoo.com/*draft*
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const BRIDGE_URL = 'http://127.0.0.1:8765';
  const NUM_TEAMS = 14;
  const TOTAL_ROUNDS = 13;
  const TOTAL_PICKS = NUM_TEAMS * TOTAL_ROUNDS; // 182
  const POLL_MS = 450;

  if (window._agyInterval) clearInterval(window._agyInterval);
  if (window._agyObserver) window._agyObserver.disconnect();
  const oldHud = document.getElementById('agy-yahoo-draft-hud');
  if (oldHud) oldHud.remove();

  window._agyNetworkPicks = window._agyNetworkPicks || [];
  window._agyBoardFullNames = window._agyBoardFullNames || new Map(); // pick -> Full Name ("Luka Dončić")
  window._agyInitialToFullName = window._agyInitialToFullName || new Map(); // "l.doncic|LAL" -> "Luka Dončić"
  window._agyHudCollapsed = window._agyHudCollapsed || false;
  let lastSyncedSignature = '';
  let syncDebounceTimer = null;
  let isSyncing = false;

  console.log(`🏀 [Antigravity] Canlı Draft Köprüsü ve HUD v5.1.0 Başlatıldı (${NUM_TEAMS} Takım, Slot #8)...`);

  // =========================================================================
  // 1. SABİTLER & İSİM TEMİZLEME MOTORU
  // =========================================================================

  const NBA_TEAMS_ARR = [
    'ATL','BOS','BKN','BRK','CHA','CHI','CLE','DAL','DEN','DET',
    'GSW','GS','HOU','IND','LAC','LAL','MEM','MIA','MIL','MIN',
    'NOP','NO','NYK','NY','OKC','ORL','PHI','PHX','PHO','POR',
    'SAC','SAS','SA','TOR','UTA','UTH','WAS'
  ];
  const NBA_TEAMS = NBA_TEAMS_ARR.join('|');
  const POS_SINGLE = '(?:PG|SG|SF|PF|C|UTIL|G|F)';
  const POS_LIST = `${POS_SINGLE}(?:[\\s,\/]+${POS_SINGLE})*`;
  const INJURY_TAGS = '(?:INJ|O|GTD|Q|DTD|SUSP|OUT|IL)';

  // Bir DOM düğümünün içindeki metin parçalarını (TextNode) birbirine yapıştırmadan dizi olarak alır
  function getTextTokens(rootEl) {
    const tokens = [];
    if (!rootEl) return tokens;
    const walker = document.createTreeWalker(rootEl, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while ((node = walker.nextNode())) {
      const val = node.nodeValue.replace(/\s+/g, ' ').trim();
      if (val) tokens.push(val);
    }
    return tokens;
  }

  // "LUKA DONČIĆ" -> "Luka Dončić" (Title Case)
  function toTitleCase(str) {
    if (!str) return '';
    return str
      .toLowerCase()
      .replace(/(?:^|[\s\.\-\'])([a-z\u00C0-\u024F])/g, m => m.toUpperCase())
      .replace(/\b(Ii|Iii|Iv)\b/g, m => m.toUpperCase());
  }

  // İsimdeki pozisyon, takım, sakatlık rozeti (Q, O, INJ) ve menajer adı kalıntılarını temizler
  function cleanRawPlayerName(raw, isAbbreviatedSidebar = false) {
    if (!raw) return '';
    let s = String(raw).replace(/\s+/g, ' ').trim();
    if (/antigravity/i.test(s)) return '';

    // 1. Parantez içi ifadeleri sil: (PF,C - MIA)
    s = s.replace(/\s*\([^)]*\)\s*/g, ' ').trim();

    // 2. Başındaki #61, Pick 61 gibi numaraları sil
    s = s.replace(/^\s*(?:Pick|#)?\s*\d+[\.\:\-\s]+/i, '');

    // 3. Sonundaki birleşik veya ayrık "Q SG,SF · CHA", "O C · GSW", "PG,SG - LAL" ifadelerini sil
    const tailRegex = new RegExp(
      `(?:\\s+${INJURY_TAGS})?\\s*${POS_LIST}\\s*[\\-\\|·•]?\\s*(?:${NBA_TEAMS})$`,
      'i'
    );
    s = s.replace(tailRegex, '');

    // 4. Eğer bitişik yazılmışsa (Örn: "B. LopezCLAC" veya "G. AllenQSG,SFCHA")
    const stuckRegex = new RegExp(
      `([a-z\\u00C0-\\u024F])(?:${INJURY_TAGS})?(${POS_LIST})[\\-\\|·•\\s]*(${NBA_TEAMS})$`
    );
    const stuckMatch = s.match(stuckRegex);
    if (stuckMatch) {
      s = s.slice(0, stuckMatch.index + 1);
    }

    // 5. Sonunda tek başına kalan sakatlık harfi varsa ("D. MURRAY Q" veya "B. INGRAM O") temizle
    s = s.replace(new RegExp(`\\s+${INJURY_TAGS}$`, 'i'), '');

    // 6. Eğer Sol Menüden ("Picks") geliyorsa, başında menajer adı kalmış olabilir:
    // Örn: "YC J. Embiid" -> "J. Embiid", "thomas I. Zubac" -> "I. Zubac", "You A. Sarr" -> "A. Sarr"
    if (isAbbreviatedSidebar) {
      const abbrMatch = s.match(/([A-Za-z\u00C0-\u024F]{1,2}\.\s+[A-Za-z\u00C0-\u024F\'\-]+(?:\s+(?:Jr\.?|Sr\.?|II|III|IV))?)$/i);
      if (abbrMatch) {
        s = abbrMatch[1];
      }
    }

    s = s.replace(/[\.\s…]+$/, item => (item.trim() === '.' && /\b(Jr|Sr)$/i.test(s.slice(0, -item.length)) ? '.' : '')).trim();
    if (!s || s.length < 3 || /^\d+$/.test(s)) return '';
    if (/^(round|pick|team|slot|empty|joined|on the clock|draft|players|board|results|standings|you)$/i.test(s)) return '';

    // Tamamı büyük harfse Title Case yap
    if (s === s.toUpperCase()) {
      s = toTitleCase(s);
    }
    return s;
  }

  // Tam ismi ("Luka Dončić") önbelleğe kaydeder ki sol menüde "L. Dončić" görürsek tam isme çevirebilelim
  function cacheFullName(fullName, teamCode = '') {
    const clean = cleanRawPlayerName(fullName, false);
    if (!clean || /^[A-Za-z]\.\s/.test(clean)) return; // Kısaltılmışsa kaydetme
    const parts = clean.split(' ');
    if (parts.length >= 2) {
      const firstInitial = parts[0][0].toLowerCase();
      const lastName = parts.slice(1).join(' ').toLowerCase();
      window._agyInitialToFullName.set(`${firstInitial}.${lastName}`, clean);
      if (teamCode) {
        window._agyInitialToFullName.set(`${firstInitial}.${lastName}|${teamCode.toUpperCase()}`, clean);
      }
    }
  }

  function resolveBestName(name, teamCode = '', pickNum = null) {
    if (pickNum && window._agyBoardFullNames.has(pickNum)) {
      return window._agyBoardFullNames.get(pickNum);
    }
    const m = name.match(/^([A-Za-z\u00C0-\u024F])\.\s+(.+)$/);
    if (m) {
      const init = m[1].toLowerCase();
      const last = m[2].toLowerCase();
      if (teamCode) {
        const byTeam = window._agyInitialToFullName.get(`${init}.${last}|${teamCode.toUpperCase()}`);
        if (byTeam) return byTeam;
      }
      const byLast = window._agyInitialToFullName.get(`${init}.${last}`);
      if (byLast) return byLast;
    }
    return name;
  }

  // =========================================================================
  // 2. SEÇİLMEMİŞ OYUNCULAR ("PLAYERS" SEKMESİ) KORUMA KALKANI
  // =========================================================================

  // Bir elemanın orta ekrandaki "Players" (seçilmemiş oyuncular) tablosunda olup olmadığını tespit eder
  function isInsideAvailablePlayersTable(el) {
    if (!el || !el.closest) return false;
    const table = el.closest('table, [role="grid"], [role="table"]');
    if (!table) return false;
    const headerText = (table.querySelector('thead')?.textContent || table.textContent.slice(0, 300) || '');
    // Eğer tablo başlığında XRank, ADP, FG%, 3PTM gibi istatistik sütunları varsa bu kesinlikle Players tablosudur!
    if (/\b(XRank|ADP|FG%|FT%|3PTM|PTS|REB)\b/i.test(headerText)) {
      return true;
    }
    return false;
  }

  // =========================================================================
  // 3. BOARD, SOL MENÜ ("PICKS") VE RESULTS TARAYICILARI
  // =========================================================================

  // A. MERKEZ "BOARD" IZGARASI TARAYICISI (Tam İsimleri Yakalar: "LUKA DONČIĆ", "VICTOR WEMBANYAMA" vb.)
  function scanBoardCellsFromDOM() {
    const picks = [];
    const seen = new Set();
    const nodes = document.querySelectorAll('div, td, li, [role="gridcell"]');

    for (const el of nodes) {
      if (el.closest && el.closest('#agy-yahoo-draft-hud')) continue;
      if (isInsideAvailablePlayersTable(el)) continue;
      if (el.children.length < 1 || el.children.length > 8) continue;

      const tokens = getTextTokens(el);
      if (tokens.length < 2 || tokens.length > 7) continue;

      // Board hücresinin sağ altındaki "1.1", "2.14", "5.6" rozetini bul
      let rnd = null;
      let inRnd = null;
      let badgeTokIdx = -1;

      for (let i = 0; i < tokens.length; i++) {
        const bm = tokens[i].match(/^([1-9]|1[0-3])\.([1-9]|1[0-4])$/);
        if (bm) {
          rnd = parseInt(bm[1], 10);
          inRnd = parseInt(bm[2], 10);
          badgeTokIdx = i;
          break;
        }
      }

      if (!rnd || !inRnd) continue;

      // Ekran görüntüsü 1'de kanıtlandığı üzere Yahoo Board'da 2. turda sağdan sola "2.1, 2.2 ... 2.14" yazıyor!
      // Yani "2.14" doğrudan 2. turun 14. seçimi = (2-1)*14 + 14 = 28. seçimdir!
      const overallPick = (rnd - 1) * NUM_TEAMS + inRnd;
      if (overallPick < 1 || overallPick > TOTAL_PICKS || seen.has(overallPick)) continue;

      // Hücredeki takım/pozisyon bilgisini ve üstteki oyuncu adını ayır
      // Örn: tokens = ["LUKA", "DONČIĆ", "PG · LAL", "1.1"] veya ["LUKA DONČIĆ", "PG", "·", "LAL", "1.1"]
      let teamCode = '';
      const nameParts = [];

      for (let i = 0; i < badgeTokIdx; i++) {
        const tok = tokens[i].trim();
        if (!tok) continue;
        // Eğer "PG · LAL" veya "PF,C · MIA" ise
        const ptMatch = tok.match(new RegExp(`^(${POS_LIST})?\\s*[\\-\\|·•]?\\s*(?:${NBA_TEAMS})$`, 'i'));
        if (ptMatch) {
          teamCode = ptMatch[2];
          continue;
        }
        if (new RegExp(`^(${POS_LIST}|${INJURY_TAGS}|[\\-\\|·•])$`, 'i').test(tok)) {
          continue;
        }
        nameParts.push(tok);
      }

      if (nameParts.length > 0) {
        const fullRaw = nameParts.join(' ');
        const cleanFull = cleanRawPlayerName(fullRaw, false);
        if (cleanFull && cleanFull.length >= 3) {
          seen.add(overallPick);
          // Board'da tam isim yazdığı için bunu kalıcı hafızaya kaydet!
          window._agyBoardFullNames.set(overallPick, cleanFull);
          cacheFullName(cleanFull, teamCode);
          picks.push({ pick: overallPick, player_name: cleanFull });
        }
      }
    }
    return picks;
  }

  // B. SOL KENAR ÇUBUĞU ("PICKS" SEKMESİ) TARAYICISI
  function scanSidebarPicksFromDOM() {
    const picks = [];
    const seen = new Set();

    const nodes = document.querySelectorAll('li, [role="listitem"], div');
    for (const el of nodes) {
      if (el.closest && el.closest('#agy-yahoo-draft-hud')) continue;
      // KRİTİK KORUMA: Orta ekrandaki "Players" tablosunu kesinlikle dışarıda bırak!
      if (isInsideAvailablePlayersTable(el)) continue;
      if (el.children.length < 1 || el.children.length > 10) continue;

      const tokens = getTextTokens(el);
      if (tokens.length < 3 || tokens.length > 12) continue;

      // Eğer içinde "Joined" veya tablo başlığı varsa atla
      const joinedStr = tokens.join(' ');
      if (/\b(joined|XRank|ADP|Queue\s+Player)\b/i.test(joinedStr)) continue;
      // Eğer Board hücresiyse (1.1, 2.14 rozeti varsa) onu scanBoardCellsFromDOM hallediyor, atla
      if (tokens.some(t => /^([1-9]|1[0-3])\.([1-9]|1[0-4])$/.test(t))) continue;

      // 1. Önce bu kutuda 1..182 arası TAM SAYI olan Pick numarasını bul
      let pickNum = null;
      let pickTokIdx = -1;
      for (let i = 0; i < tokens.length; i++) {
        if (/^[1-9]\d{0,2}$/.test(tokens[i])) {
          const n = parseInt(tokens[i], 10);
          if (n >= 1 && n <= TOTAL_PICKS) {
            pickNum = n;
            pickTokIdx = i;
            break;
          }
        }
      }
      if (!pickNum || seen.has(pickNum)) continue;

      // 2. Pick numarasından SONRA gelen token'lar içinde "Başharf. Soyadı" (Örn: "J. EMBIID", "I. ZUBAC", "N. ALEXANDER-WALKER") ara!
      // Not: Menajer adı ("thomas", "Miles", "You", "Jo") her zaman pick numarasından ÖNCE veya baş harfsiz gelir.
      let rawPlayerName = '';
      let teamCode = '';

      for (let i = pickTokIdx + 1; i < tokens.length; i++) {
        const tok = tokens[i];
        // Takım kodunu yakala
        const tm = tok.match(new RegExp(`\\b(${NBA_TEAMS})\\b`, 'i'));
        if (tm) teamCode = tm[1];

        // "J. EMBIID" veya "S. GILGEOUS-ALEXANDER" kalıbı:
        if (!rawPlayerName && /^[A-Za-z\u00C0-\u024F]{1,2}\.\s+[A-Za-z\u00C0-\u024F]/.test(tok)) {
          rawPlayerName = tok;
        }
      }

      if (!rawPlayerName) continue;

      const cleaned = cleanRawPlayerName(rawPlayerName, true);
      if (cleaned && cleaned.length >= 3) {
        const finalName = resolveBestName(cleaned, teamCode, pickNum);
        seen.add(pickNum);
        picks.push({ pick: pickNum, player_name: finalName });
      }
    }
    return picks;
  }

  // C. "RESULTS" SEKMESİ TARAYICISI
  function scanResultsTabFromDOM() {
    const picks = [];
    const seen = new Set();
    const rows = document.querySelectorAll('tr, [role="row"]');
    for (const row of rows) {
      if (row.closest && row.closest('#agy-yahoo-draft-hud')) continue;
      if (isInsideAvailablePlayersTable(row)) continue;

      const tokens = getTextTokens(row);
      if (tokens.length < 2 || tokens.length > 10) continue;

      let pNum = null;
      for (const tok of tokens) {
        const m = tok.match(/^(?:#|Pick\s*)?([1-9]\d{0,2})\.?$/i);
        if (m) {
          const n = parseInt(m[1], 10);
          if (n >= 1 && n <= TOTAL_PICKS) {
            pNum = n;
            break;
          }
        }
      }
      if (!pNum || seen.has(pNum)) continue;

      const nameEl = row.querySelector('a[href*="/players/"], a[href*="/nba/"], [class*="name"], [class*="player"], strong');
      if (nameEl) {
        const cleaned = cleanRawPlayerName(nameEl.textContent, false);
        if (cleaned && cleaned.length >= 3) {
          cacheFullName(cleaned);
          window._agyBoardFullNames.set(pNum, cleaned);
          seen.add(pNum);
          picks.push({ pick: pNum, player_name: cleaned });
        }
      }
    }
    return picks;
  }

  // D. AĞ VE REACT FIBER TARAYICISI
  function extractPicksFromPayload(root) {
    const picks = [];
    const visited = new Set();
    function recurse(obj, depth) {
      if (!obj || depth > 9 || typeof obj !== 'object' || visited.has(obj)) return;
      visited.add(obj);
      if (Array.isArray(obj)) {
        for (const item of obj) recurse(item, depth + 1);
        return;
      }

      // Tam isim önbelleğini besle (Players tablosundaki oyuncuların tam isimlerini de önbelleğe alır ki "J. Embiid" -> "Joel Embiid" dönüşsün!)
      const fullName = obj.full_name || obj.displayName || (obj.name && obj.name.full) || obj.player_name || obj.playerName;
      const teamAbbr = obj.editorial_team_abbr || obj.team_abbr || obj.team || '';
      if (typeof fullName === 'string' && fullName.length > 4) {
        cacheFullName(fullName, typeof teamAbbr === 'string' ? teamAbbr : '');
      }

      // Sadece gerçek draft pick nesnelerini al (rank veya xrank'i pick sanmaması için sıkı kontrol)
      const pNum = obj.pick_number ?? obj.overall_pick ?? obj.pickNumber ?? obj.overallPick ?? obj.draft_pick;
      const pName =
        obj.player_name ||
        obj.playerName ||
        (obj.player && (obj.player.name?.full || obj.player.name || obj.player.displayName || obj.player.full_name));

      if (pNum !== undefined && pNum !== null && pName && typeof pName === 'string') {
        const parsedNum = parseInt(pNum, 10);
        const cleaned = cleanRawPlayerName(pName, false);
        if (!isNaN(parsedNum) && parsedNum >= 1 && parsedNum <= TOTAL_PICKS && cleaned.length >= 3) {
          cacheFullName(cleaned, typeof teamAbbr === 'string' ? teamAbbr : '');
          window._agyBoardFullNames.set(parsedNum, cleaned);
          picks.push({ pick: parsedNum, player_name: cleaned });
        }
      }

      for (const key of Object.keys(obj)) {
        if (key === 'window' || key === 'document' || key.startsWith('_')) continue;
        const val = obj[key];
        if (val && typeof val === 'object') recurse(val, depth + 1);
      }
    }
    recurse(root, 0);
    return picks;
  }

  function scanDraftRootFiber() {
    const allPicksMap = new Map();
    try {
      const sampleNodes = document.querySelectorAll('#atomic, #draft, #app, #root, main, section, table, [role="grid"]');
      const roots = [document.body, ...Array.from(sampleNodes).slice(0, 25)];
      const visitedFibers = new Set();

      for (const rootEl of roots) {
        if (!rootEl) continue;
        const key = Object.keys(rootEl).find(k => k.startsWith('__reactFiber$') || k.startsWith('__reactInternalInstance$'));
        if (!key) continue;

        let fiber = rootEl[key];
        let steps = 0;
        while (fiber && steps < 350) {
          steps++;
          if (!visitedFibers.has(fiber)) {
            visitedFibers.add(fiber);
            for (const obj of [fiber.memoizedState, fiber.memoizedProps, fiber.stateNode?.state, fiber.stateNode?.props]) {
              if (!obj || typeof obj !== 'object') continue;
              for (const p of extractPicksFromPayload(obj)) {
                if (p && p.pick && p.player_name && !allPicksMap.has(p.pick)) {
                  allPicksMap.set(p.pick, p);
                }
              }
            }
          }
          if (fiber.child) fiber = fiber.child;
          else {
            while (fiber) {
              if (fiber.sibling) { fiber = fiber.sibling; break; }
              fiber = fiber.return;
            }
          }
        }
      }
    } catch (e) {}
    return Array.from(allPicksMap.values());
  }

  // Tüm kaynakları birleştirir; her zaman TAM İSİM ("Luka Dončić") olanı kısaltılmış isme ("L. Dončić") tercih eder!
  function aggregateAllPicks() {
    const pickMap = new Map();

    const addOrUpgradePick = (p) => {
      if (!p || !p.pick || !p.player_name) return;
      const existing = pickMap.get(p.pick);
      const bestName = resolveBestName(p.player_name, '', p.pick);
      if (!existing) {
        pickMap.set(p.pick, bestName);
      } else {
        // Eğer mevcut isim kısaltılmışsa ("L. Dončić") ve yeni gelen tam isimse ("Luka Dončić"), tam isimle güncelle!
        const isExistingAbbr = /^[A-Za-z\u00C0-\u024F]{1,2}\.\s/.test(existing);
        const isNewAbbr = /^[A-Za-z\u00C0-\u024F]{1,2}\.\s/.test(bestName);
        if (isExistingAbbr && !isNewAbbr) {
          pickMap.set(p.pick, bestName);
        }
      }
    };

    for (const p of scanBoardCellsFromDOM()) addOrUpgradePick(p);
    for (const p of scanResultsTabFromDOM()) addOrUpgradePick(p);
    for (const p of scanDraftRootFiber()) addOrUpgradePick(p);
    for (const p of window._agyNetworkPicks || []) addOrUpgradePick(p);
    for (const p of scanSidebarPicksFromDOM()) addOrUpgradePick(p);

    const result = [];
    for (const [pick, player_name] of pickMap.entries()) {
      result.push({ pick: parseInt(pick, 10), player_name });
    }
    result.sort((a, b) => a.pick - b.pick);
    return result;
  }

  // =========================================================================
  // 4. SUNUCU SIFIRLAMA VE BOARD TARAMA KOMUTLARI
  // =========================================================================

  function simulateReactClick(el) {
    if (!el) return;
    ['mousedown', 'mouseup', 'click'].forEach(evtType => {
      el.dispatchEvent(new MouseEvent(evtType, { bubbles: true, cancelable: true, view: window }));
    });
  }

  function tryClickTab(tabNamePattern) {
    const elements = document.querySelectorAll('button, a, [role="tab"], li, span, div');
    for (const el of elements) {
      if (el.closest && el.closest('#agy-yahoo-draft-hud')) continue;
      if (el.children.length > 1) continue;
      const text = (el.textContent || '').trim();
      if (tabNamePattern.test(text)) {
        simulateReactClick(el);
        if (el.parentElement) simulateReactClick(el.parentElement);
        return true;
      }
    }
    return false;
  }

  // Python sunucusunda birikmiş sahte (-8, -169 vb.) seçimleri geri alıp temizler ve gerçek seçimleri yükler
  window.agyResetAndResyncServer = async function () {
    const sub = document.getElementById('agy-substatus');
    if (sub) sub.textContent = '⏳ Sunucudaki hatalı seçimler temizleniyor...';

    try {
      // Önce Board sekmesine tıklayıp tam isimleri hafızaya alalım
      tryClickTab(/^Board$/i);
      await new Promise(r => setTimeout(r, 350));
      scanBoardCellsFromDOM();

      const validPicks = aggregateAllPicks();

      // Sunucudaki mevcut durumu kontrol et
      const stResp = await fetch(`${BRIDGE_URL}/api/state`);
      if (stResp.ok) {
        const stData = await stResp.json();
        const serverCount = (stData.state || stData)?.status?.total_picks_made || 0;

        // Eğer sunucuda sahte seçimler varsa (veya -8 gibi bozuk kayıtlar varsa) hepsini hızlıca undo ile sıfırla
        if (serverCount > 0) {
          for (let i = 0; i < serverCount; i++) {
            await fetch(`${BRIDGE_URL}/api/undo`, { method: 'POST' });
          }
        }
      }

      lastSyncedSignature = '';
      await performSync(true);
      alert(
        `✅ Sunucu tamamen temizlendi ve ${validPicks.length} gerçek seçim (Tam İsimleriyle) yüklendi!\n\n` +
        validPicks.slice(0, 5).map(p => `#${p.pick}: ${p.player_name}`).join('\n') +
        (validPicks.length > 5 ? `\n...\n` + validPicks.slice(-5).map(p => `#${p.pick}: ${p.player_name}`).join('\n') : '')
      );
    } catch (e) {
      alert(`Hata: ${e}`);
    }
  };

  window.agyFetchPastPicksFromBoard = function () {
    tryClickTab(/^Board$/i);
    setTimeout(() => {
      const boardPicks = scanBoardCellsFromDOM();
      const allPicks = aggregateAllPicks();
      lastSyncedSignature = '';
      performSync(true);
      if (allPicks.length > 0) {
        alert(
          `✅ Başarılı! Toplam ${allPicks.length} seçim (${boardPicks.length} tanesi Board tam ismiyle) yakalandı:\n\n` +
          allPicks.slice(-8).map(p => `#${p.pick}: ${p.player_name}`).join('\n')
        );
      } else {
        window.agyDiagnose();
      }
    }, 350);
  };

  // =========================================================================
  // 5. FLOATING HUD OVERLAY (SOL ALT & AÇILIR/KAPANIR)
  // =========================================================================

  function createHudOverlay() {
    let box = document.getElementById('agy-yahoo-draft-hud');
    if (box) return;
    box = document.createElement('div');
    box.id = 'agy-yahoo-draft-hud';
    box.style.cssText = [
      'position:fixed', 'bottom:14px', 'left:14px', 'width:430px', 'max-height:90vh',
      'background:rgba(11, 15, 25, 0.97)', 'color:#f8fafc', 'border:1px solid #334155',
      'border-radius:12px', 'box-shadow:0 14px 34px rgba(0,0,0,0.75)',
      'font-family:Segoe UI, system-ui, sans-serif', 'font-size:12px', 'z-index:9999999',
      'padding:10px 12px', 'backdrop-filter:blur(8px)', 'display:flex', 'flex-direction:column',
      'gap:8px', 'overflow:hidden', 'transition:width 0.2s, max-height 0.2s'
    ].join(';');

    box.innerHTML = `
      <div id="agy-hud-header" style="display:flex;justify-content:space-between;align-items:center;cursor:pointer;user-select:none;border-bottom:1px solid #1e293b;padding-bottom:6px;">
        <div style="display:flex;align-items:center;gap:6px;">
          <button id="agy-btn-toggle" style="background:#1e293b;color:#38bdf8;border:1px solid #334155;border-radius:4px;width:22px;height:22px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:11px;font-weight:700;padding:0;" title="Paneli Küçült / Büyüt">▼</button>
          <div>
            <strong style="font-size:13px;color:#38bdf8;">🏀 Antigravity AI Draft v5.1 (Slot #<span id="agy-slot">8</span>)</strong>
            <div id="agy-substatus" style="font-size:11px;color:#94a3b8;margin-top:1px;">Köprü bağlanıyor (127.0.0.1:8765)...</div>
          </div>
        </div>
        <div style="display:flex;gap:6px;align-items:center;">
          <span id="agy-sync-badge" style="font-size:10px;padding:3px 6px;border-radius:4px;background:#1e293b;color:#38bdf8;">0/${TOTAL_PICKS} Pick</span>
          <span id="agy-turn-pill" style="padding:4px 8px;border-radius:5px;font-weight:700;font-size:11px;background:#1e293b;color:#94a3b8;">Bekleniyor</span>
        </div>
      </div>

      <div id="agy-hud-body" style="display:flex;flex-direction:column;gap:8px;">
        <div style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:6px 8px;display:flex;justify-content:space-between;align-items:center;gap:4px;">
          <span id="agy-dom-counter" style="font-size:11px;color:#cbd5e1;">Ekrandan: 0 | Sunucu: 0</span>
          <div style="display:flex;gap:4px;">
            <button id="agy-btn-board-sync" style="background:#2563eb;color:#fff;border:none;border-radius:4px;padding:4px 8px;cursor:pointer;font-size:11px;font-weight:600;" title="Board sekmesinden tam isimleri çek">📋 Board'u Tara</button>
            <button id="agy-btn-hard-reset" style="background:#dc2626;color:#fff;border:none;border-radius:4px;padding:4px 8px;cursor:pointer;font-size:11px;font-weight:600;" title="Sunucudaki sahte (-169 vb.) seçimleri silip baştan temiz kur">🗑️ Sıfırla & Kur</button>
          </div>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="color:#cbd5e1;font-weight:600;font-size:12px;">🎯 En İyi H2H Rollout Önerileri:</span>
          <button id="agy-btn-rescan" style="background:#1e293b;color:#38bdf8;border:1px solid #334155;border-radius:4px;padding:2px 6px;cursor:pointer;font-size:11px;">🔄 Zorla Eşitle</button>
        </div>

        <div id="agy-recs-container" style="overflow-y:auto;max-height:210px;display:flex;flex-direction:column;gap:4px;"></div>
        <div id="agy-cats-bar" style="font-size:10px;color:#94a3b8;line-height:1.5;border-top:1px solid #1e293b;padding-top:6px;"></div>

        <div style="border-top:1px solid #1e293b;padding-top:8px;">
          <div style="display:flex;gap:4px;margin-bottom:4px;">
            <input type="text" id="agy-fast-input" placeholder="Hızlı manuel seçim (Örn: jokic, doncic)..." style="flex:1;background:#0f172a;border:1px solid #334155;color:#fff;padding:5px 8px;border-radius:5px;font-size:11px;" />
            <button id="agy-btn-fast-opp" style="background:#dc2626;color:#fff;border:none;border-radius:5px;padding:5px 8px;cursor:pointer;font-size:11px;font-weight:600;">⚡ Rakip</button>
            <button id="agy-btn-fast-mine" style="background:#059669;color:#fff;border:none;border-radius:5px;padding:5px 8px;cursor:pointer;font-size:11px;font-weight:600;">🏆 Biz</button>
            <button id="agy-btn-undo" style="background:#475569;color:#fff;border:none;border-radius:5px;padding:5px 8px;cursor:pointer;font-size:11px;" title="Son seçimi geri al">↩</button>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:10px;color:#64748b;">
            <span id="agy-last-pick-label">Son: Yok</span>
            <button id="agy-btn-diag" style="background:none;border:none;color:#64748b;text-decoration:underline;cursor:pointer;padding:0;font-size:10px;">🧪 Teşhis / Test</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(box);

    const toggleHud = () => {
      window._agyHudCollapsed = !window._agyHudCollapsed;
      const b = document.getElementById('agy-hud-body');
      const btn = document.getElementById('agy-btn-toggle');
      const hdr = document.getElementById('agy-hud-header');
      if (b && btn) {
        if (window._agyHudCollapsed) {
          b.style.display = 'none';
          btn.textContent = '▲';
          btn.title = 'Paneli Genişlet';
          if (hdr) hdr.style.borderBottom = 'none';
          box.style.width = '390px';
        } else {
          b.style.display = 'flex';
          btn.textContent = '▼';
          btn.title = 'Paneli Küçült';
          if (hdr) hdr.style.borderBottom = '1px solid #1e293b';
          box.style.width = '430px';
        }
      }
    };

    document.getElementById('agy-btn-toggle').addEventListener('click', (e) => {
      e.stopPropagation();
      toggleHud();
    });
    document.getElementById('agy-hud-header').addEventListener('click', (e) => {
      if (e.target.tagName !== 'BUTTON') {
        toggleHud();
      }
    });

    document.getElementById('agy-btn-board-sync').addEventListener('click', () => window.agyFetchPastPicksFromBoard());
    document.getElementById('agy-btn-hard-reset').addEventListener('click', () => window.agyResetAndResyncServer());
    document.getElementById('agy-btn-rescan').addEventListener('click', () => {
      lastSyncedSignature = '';
      performSync(true);
    });
    document.getElementById('agy-btn-diag').addEventListener('click', () => window.agyDiagnose());
    document.getElementById('agy-btn-fast-opp').addEventListener('click', () => {
      const q = document.getElementById('agy-fast-input').value.trim();
      if (q) window.agyManualPick(q, false);
    });
    document.getElementById('agy-btn-fast-mine').addEventListener('click', () => {
      const q = document.getElementById('agy-fast-input').value.trim();
      if (q) window.agyManualPick(q, true);
    });
    document.getElementById('agy-btn-undo').addEventListener('click', () => window.agyUndoPick());
    document.getElementById('agy-fast-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = document.getElementById('agy-fast-input').value.trim();
        if (q) window.agyManualPick(q, false);
      }
    });

    if (window._agyHudCollapsed) {
      const b = document.getElementById('agy-hud-body');
      const btn = document.getElementById('agy-btn-toggle');
      const hdr = document.getElementById('agy-hud-header');
      if (b && btn) {
        b.style.display = 'none';
        btn.textContent = '▲';
        if (hdr) hdr.style.borderBottom = 'none';
        box.style.width = '390px';
      }
    }
  }

  window.agyFocusYahooPlayer = function (playerName) {
    const searchInputs = document.querySelectorAll(
      'input[type="search"], input[placeholder*="Search"], input[placeholder*="player"], [data-tst="player-search-input"], .player-search input'
    );
    for (const inp of searchInputs) {
      inp.focus();
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
      if (nativeSetter) nativeSetter.call(inp, playerName);
      else inp.value = playerName;
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.dispatchEvent(new Event('change', { bubbles: true }));
      break;
    }
  };

  window.agyManualPick = async function (query, isMine) {
    try {
      const resp = await fetch(`${BRIDGE_URL}/api/manual_pick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, is_mine: isMine })
      });
      if (resp.ok) {
        const data = await resp.json();
        const input = document.getElementById('agy-fast-input');
        if (input) input.value = '';
        if (data.state) renderHud(data.state, aggregateAllPicks().length);
      } else {
        const err = await resp.json();
        alert(`Uyarı: ${err.error || 'Oyuncu bulunamadı'}`);
      }
    } catch (e) {
      alert(`Sunucu hatası: ${e}`);
    }
  };

  window.agyUndoPick = async function () {
    try {
      const resp = await fetch(`${BRIDGE_URL}/api/undo`, { method: 'POST' });
      if (resp.ok) {
        const data = await resp.json();
        if (window._agyNetworkPicks && window._agyNetworkPicks.length > 0) window._agyNetworkPicks.pop();
        if (data.state) renderHud(data.state, aggregateAllPicks().length);
      }
    } catch (e) {}
  };

  window.agyDiagnose = function () {
    const sidebar = scanSidebarPicksFromDOM();
    const board = scanBoardCellsFromDOM();
    const results = scanResultsTabFromDOM();
    const fiber = scanDraftRootFiber();
    const all = aggregateAllPicks();

    console.log('====================================================');
    console.log(`🏀 [Antigravity v5.0 Teşhis Raporu]`);
    console.log(`1. Board Tam İsim Izgarası : ${board.length} seçim`, board);
    console.log(`2. Sol "Picks" Listesi     : ${sidebar.length} seçim`, sidebar);
    console.log(`3. Results Tablosu         : ${results.length} seçim`, results);
    console.log(`4. React Fiber Hafıza      : ${fiber.length} seçim`, fiber);
    console.log(`TOPLAM BİRLEŞTİRİLEN       : ${all.length} seçim`, all);
    console.table(all);
    console.log('====================================================');
    alert(
      `Teşhis Raporu (v5.0):\n` +
      `• Board Tam İsim: ${board.length} seçim\n` +
      `• Sol "Picks" Listesi: ${sidebar.length} seçim\n` +
      `• TOPLAM: ${all.length} gerçek seçim\n\n` +
      (all.length > 0 ? `Örnek Yakalananlar:\n` + all.slice(-6).map(p => `#${p.pick}: ${p.player_name}`).join('\n') : '')
    );
  };

  function parseRemainingSeconds() {
    const clockNodes = document.querySelectorAll('[data-tst="draft-clock"], [class*="timer"], [class*="clock"]');
    for (const cn of clockNodes) {
      const text = cn.textContent.trim();
      const parts = text.split(':');
      if (parts.length === 2) {
        const min = parseInt(parts[0], 10);
        const sec = parseInt(parts[1], 10);
        if (!isNaN(min) && !isNaN(sec)) return min * 60 + sec;
      }
      const m = text.match(/\b(\d{1,3})\b/);
      if (m) {
        const s = parseInt(m[1], 10);
        if (!isNaN(s)) return s;
      }
    }
    return 999;
  }

  function renderHud(data, domCount = 0) {
    createHudOverlay();
    const st = data.status || {};
    const slotEl = document.getElementById('agy-slot');
    if (slotEl) slotEl.textContent = st.my_slot || 8;

    const domCounterEl = document.getElementById('agy-dom-counter');
    if (domCounterEl) {
      domCounterEl.textContent = `Ekrandan: ${domCount} | Sunucu: ${st.total_picks_made || 0}`;
      domCounterEl.style.color = domCount > 0 && domCount === st.total_picks_made ? '#34d399' : '#fbbf24';
    }

    const substatusEl = document.getElementById('agy-substatus');
    if (substatusEl) {
      substatusEl.textContent = `Pick #${st.overall_pick || 1} (Tur ${st.round || 1}.${st.pick_in_round || 1}) | Hız: ${(data.elapsed_ms || 0).toFixed(0)}ms`;
    }

    const syncBadge = document.getElementById('agy-sync-badge');
    if (syncBadge) {
      syncBadge.textContent = `${st.total_picks_made || 0}/${TOTAL_PICKS} Pick`;
    }

    const pill = document.getElementById('agy-turn-pill');
    if (pill) {
      if (st.is_my_turn) {
        pill.style.background = '#059669';
        pill.style.color = '#ffffff';
        pill.textContent = '⚡ SIRA SENDE!';
      } else {
        pill.style.background = '#1e293b';
        pill.style.color = '#94a3b8';
        pill.textContent = `${st.picks_until_mine || 0} seçim kaldı`;
      }
    }

    const secLeft = parseRemainingSeconds();
    if (pill && st.is_my_turn && secLeft <= 10) {
      pill.style.background = '#dc2626';
      pill.style.color = '#ffffff';
      pill.textContent = `⚠️ SÜRE AZALIYOR (${secLeft}s)!`;
    }

    const lastLabel = document.getElementById('agy-last-pick-label');
    if (lastLabel && data.recent_picks && data.recent_picks.length > 0) {
      const lp = data.recent_picks[0];
      lastLabel.textContent = `Son: #${lp.overall} ${lp.name} (Slot #${lp.slot}${lp.is_mine ? ' - BİZ' : ''})`;
    }

    const recsDiv = document.getElementById('agy-recs-container');
    if (recsDiv) {
      const top5 = (data.recommendations || []).slice(0, 5);
      const newRecsHtml = top5
        .map(
          (r, i) => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 7px;border-radius:6px;background:${i === 0 ? '#064e3b' : '#111827'};border:1px solid ${i === 0 ? '#10b981' : '#1f2937'};">
          <div style="flex:1;overflow:hidden;margin-right:6px;">
            <div style="display:flex;align-items:center;gap:4px;">
              <strong style="color:${i === 0 ? '#34d399' : '#f1f5f9'};font-size:12px;">#${i + 1} ${r.NAME}</strong>
              <span style="color:#94a3b8;font-size:10px;">(${r.TEAM} - ${r.POS})</span>
            </div>
            <div style="font-size:10px;color:#cbd5e1;margin-top:1px;">E[Wins]: <b>${(r.WIN_PROB_SCORE || 0).toFixed(2)}/9</b> | FastZ: ${(r.FAST_SCORE >= 0 ? '+' : '')}${(r.FAST_SCORE || 0).toFixed(2)} | ${r.Active_Punts || 'Dengeli'}</div>
          </div>
          <div style="display:flex;gap:3px;align-items:center;">
            <button onclick="window.agyFocusYahooPlayer('${String(r.NAME).replace(/'/g, "\\'")}')" style="background:#2563eb;color:#fff;border:none;border-radius:4px;padding:3px 6px;cursor:pointer;font-size:10px;font-weight:600;" title="Yahoo arama kutusuna yaz">Bul</button>
            <button onclick="window.agyManualPick('${r.ID}', false)" style="background:#334155;color:#e2e8f0;border:none;border-radius:4px;padding:3px 5px;cursor:pointer;font-size:10px;" title="Rakip bu oyuncuyu aldı">Rakip</button>
            <button onclick="window.agyManualPick('${r.ID}', true)" style="background:#059669;color:#fff;border:none;border-radius:4px;padding:3px 5px;cursor:pointer;font-size:10px;" title="Biz seçtik">Biz</button>
          </div>
        </div>
      `
        )
        .join('');

      if (recsDiv.dataset.lastHtml !== newRecsHtml) {
        recsDiv.innerHTML = newRecsHtml;
        recsDiv.dataset.lastHtml = newRecsHtml;
      }
    }

    const catsBar = document.getElementById('agy-cats-bar');
    if (catsBar) {
      const probs = data.category_win_probs || {};
      const newCatsHtml = Object.entries(probs)
        .map(([k, v]) => {
          const color = v >= 0.52 ? '#34d399' : v < 0.38 ? '#f87171' : '#94a3b8';
          return `<span style="color:${color}"><b>${k}:</b> %${(v * 100).toFixed(0)}</span>`;
        })
        .join(' · ');

      if (catsBar.dataset.lastHtml !== newCatsHtml) {
        catsBar.innerHTML = newCatsHtml;
        catsBar.dataset.lastHtml = newCatsHtml;
      }
    }
  }

  // =========================================================================
  // 6. ANA SENKRONİZASYON DÖNGÜSÜ
  // =========================================================================

  async function performSync(forcePost = false) {
    if (isSyncing) return;
    isSyncing = true;
    try {
      const allPicks = aggregateAllPicks();
      const currentSignature = allPicks.map(p => `${p.pick}:${p.player_name}`).join('|');
      let resp;

      if (allPicks.length > 0 && (forcePost || currentSignature !== lastSyncedSignature)) {
        lastSyncedSignature = currentSignature;
        resp = await fetch(`${BRIDGE_URL}/api/sync_picks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ picks: allPicks, my_slot: 8 })
        });
      } else {
        resp = await fetch(`${BRIDGE_URL}/api/state`);
      }

      if (resp && resp.ok) {
        const data = await resp.json();
        const stateObj = data.state || data;
        renderHud(stateObj, allPicks.length);
      }
    } catch (err) {
      createHudOverlay();
      const sub = document.getElementById('agy-substatus');
      if (sub) {
        sub.textContent = '⚠️ Yerel sunucu bekleniyor (Terminalden python src/live_draft_assistant.py çalıştırın)';
      }
    } finally {
      isSyncing = false;
    }
  }

  function scheduleFastSync(delayMs = 80) {
    if (syncDebounceTimer) clearTimeout(syncDebounceTimer);
    syncDebounceTimer = setTimeout(() => performSync(false), delayMs);
  }

  window._agyObserver = new MutationObserver((mutations) => {
    const isExternalChange = mutations.some(m => {
      const t = m.target;
      const el = t && t.nodeType === 1 ? t : (t ? t.parentElement : null);
      return !el || !el.closest('#agy-yahoo-draft-hud');
    });
    if (isExternalChange) {
      scheduleFastSync(120);
    }
  });
  window._agyObserver.observe(document.body, { childList: true, subtree: true });

  window._agyInterval = setInterval(() => performSync(false), POLL_MS);
  performSync(true);
})();
