// Runs inside the existing same-origin Yahoo bookmarklet. No scores, roster
// overlap or NBA dates are used to invent fantasy opponents or period boundaries.
function parseYahooFantasyPeriod(text, season) {
  const seasonMatch = String(season || '').match(/^(20\d{2})_(\d{2})$/);
  if (!seasonMatch || Number(seasonMatch[2]) !== (Number(seasonMatch[1]) + 1) % 100) return null;
  const year = Number(seasonMatch[1]);
  const iso = text.match(/\b20\d{2}-\d{2}-\d{2}\b/g);
  let dates;
  if (iso && iso.length === 2) dates = iso;
  else {
    const months = {jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12};
    const range = text.match(/\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:,?\s+(20\d{2}))?\s*[-–—]\s*(?:([A-Za-z]{3,9})\.?\s+)?(\d{1,2})(?:,?\s+(20\d{2}))?\b/);
    if (!range) return null;
    const a = months[range[1].slice(0,3).toLowerCase()], b = months[(range[4] || range[1]).slice(0,3).toLowerCase()];
    if (!a || !b) return null;
    const years = [year + (a < 7 ? 1 : 0), year + (b < 7 ? 1 : 0)];
    if ((range[3] && Number(range[3]) !== years[0]) || (range[6] && Number(range[6]) !== years[1])) return null;
    dates = [[a, range[2]], [b, range[5]]].map(([m,d],i) => `${years[i]}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`);
  }
  const stamps = dates.map(date => new Date(date + 'T00:00:00Z'));
  if (stamps.some((stamp,i) => !Number.isFinite(stamp.getTime()) || stamp.toISOString().slice(0,10) !== dates[i])) return null;
  if (stamps[1] < stamps[0] || (stamps[1] - stamps[0]) / 86400000 > 20) return null;
  if (dates[0] < `${year}-07-01` || dates[1] >= `${year+1}-07-01`) return null;
  return dates;
}

// Same-origin Yahoo capture. Dates and provider IDs prove every matchup.
function parseYahooDatedMatchup(hrefs, displayedWeek, leagueId, origin) {
  const week = Number(String(displayedWeek || '').match(/\bWeek\s+(\d+)\b/i)?.[1]);
  if (!Number.isInteger(week) || week < 1 || week > 60) return null;
  const records = [];
  for (const href of hrefs) {
    let url;
    try { url = new URL(href, origin); } catch (_) { continue; }
    if (url.origin !== origin || url.pathname !== `/nba/${leagueId}/matchup` || Number(url.searchParams.get('week')) !== week) continue;
    const date = url.searchParams.get('date'), a = url.searchParams.get('mid1'), b = url.searchParams.get('mid2');
    if (!/^20\d{2}-\d{2}-\d{2}$/.test(date || '') || !/^[1-9]\d*$/.test(a || '') || !/^[1-9]\d*$/.test(b || '') || a === b) continue;
    records.push({date, pair:[a,b].sort((x,y)=>Number(x)-Number(y))});
  }
  if (!records.length || new Set(records.map(row=>row.pair.join('/'))).size !== 1) return null;
  const dates = [...new Set(records.map(row=>row.date))].sort();
  const first = new Date(dates[0]+'T00:00:00Z');
  if (!Number.isFinite(first.getTime()) || dates.length < 2 || dates.length > 21 || dates.some((date,i)=>new Date(first.getTime()+i*86400000).toISOString().slice(0,10) !== date)) return null;
  const year = Number(dates[0].slice(0,4))-(Number(dates[0].slice(5,7)) < 7 ? 1 : 0);
  const season = `${year}_${String(year+1).slice(-2)}`;
  if (!parseYahooFantasyPeriod(`${dates[0]} ${dates.at(-1)}`,season)) return null;
  return {week,start:dates[0],end:dates.at(-1),dates,pair:records[0].pair,season};
}

function readYahooMatchupEvidence(doc, leagueId, origin) {
  const nav=doc.querySelector('#matchup_selectlist_nav');
  const label = nav && (nav.getAttribute('aria-label') || nav.getAttribute('title') || nav.textContent) || Array.from(doc.querySelectorAll('select option:checked')).map(el=>el.textContent || '').find(text=>/\bWeek\s+\d+\b/i.test(text));
  return parseYahooDatedMatchup(Array.from(doc.querySelectorAll('a[href]')).map(a=>a.getAttribute('href')),label,leagueId,origin);
}

function parseYahooStage5Page(doc,leagueId,origin,currentWeek) {
  const result={source:'yahoo_browser_league',league_id:String(leagueId),pending_offers:{scan_complete:false,reason:'Pending trade page markup has not been verified'}};
  const teamID=href=>{try{const url=new URL(href,origin);return url.origin===origin && url.pathname.match(new RegExp(`^/nba/${leagueId}/(\\d+)/?$`))?.[1];}catch(_){return null;}};
  for(const table of doc.querySelectorAll('table')) {
    const headers=Array.from(table.querySelectorAll('thead th, tr:first-child th')).map(el=>(el.textContent || '').replace(/\s+/g,' ').trim());
    const index=headers.findIndex(text=>/^W\s*-\s*L\s*-\s*T$/i.test(text));
    if(index<0) continue;
    const records={}; let invalid=false;
    for(const row of table.querySelectorAll('tbody tr')) {
      const ids=[...new Set(Array.from(row.querySelectorAll('a[href]')).map(a=>teamID(a.getAttribute('href'))).filter(Boolean))];
      if(ids.length!==1) continue;
      const text=(row.querySelectorAll('th,td')[index]?.textContent || '').trim();
      const values=text.match(/^(\d+)\s*-\s*(\d+)\s*-\s*(\d+)$/);
      if(!values) {invalid=true;continue;}
      const [W,L,T]=values.slice(1).map(Number);records[ids[0]]={W,L,T};
    }
    if(!invalid && Object.keys(records).length===14 && Number.isInteger(currentWeek) && Object.values(records).every(r=>r.W+r.L+r.T===9*(currentWeek-1))) result.standings={current_week:currentWeek,completed_through_week:currentWeek-1,records,tiebreak_rule:'unverified'};
  }
  const container=doc.querySelector('#pending-trades, [data-pending-trades]');
  if(container) {
    const nodes=Array.from(container.querySelectorAll('[data-transaction-key]'));
    const offers=[];let invalid=false;
    for(const node of nodes) {
      const offer_id=node.getAttribute('data-transaction-key'), trader_team_key=node.getAttribute('data-trader-team-key'),tradee_team_key=node.getAttribute('data-tradee-team-key'),status=node.getAttribute('data-status');
      const players=Array.from(node.querySelectorAll('[data-player-id]')).map(el=>({yahoo_player_id:el.getAttribute('data-player-id'),source_team_key:el.getAttribute('data-source-team-key'),destination_team_key:el.getAttribute('data-destination-team-key')}));
      if(!offer_id || !trader_team_key || !tradee_team_key || !status || !players.length || players.some(p=>!p.yahoo_player_id || !p.source_team_key || !p.destination_team_key)) {invalid=true;continue;}
      offers.push({offer_id,trader_team_key,tradee_team_key,status,players});
    }
    const explicitEmpty=/\bno (?:pending )?trade (?:offers?|proposals?)\b/i.test(container.textContent || '');
    if(!invalid && (offers.length || explicitEmpty)) result.pending_offers={scan_complete:true,offers};
  }
  return result;
}

function readYahooLeagueWeek(doc,leagueId,origin) {
  const root=doc.querySelector('#matchupweek');
  if(!root) return null;
  const labels=[...(root.textContent || '').matchAll(/\bWeek\s+(\d+)\s+Matchups\b/gi)];
  const numbers=new Set(labels.map(match=>Number(match[1])));
  if(numbers.size!==1) return null;
  const pairs=new Map();
  for(const card of root.querySelectorAll('li')) {
    const teams=new Set();
    for(const anchor of card.querySelectorAll('a[href]')) {
      let url;try{url=new URL(anchor.getAttribute('href'),origin);}catch(_){continue;}
      if(url.origin!==origin) continue;
      const match=url.pathname.match(new RegExp(`^/nba/${leagueId}/(\\d+)/?$`));
      if(match) teams.add(match[1]);
    }
    if(teams.size!==2) continue;
    const pair=[...teams].sort((a,b)=>Number(a)-Number(b));pairs.set(pair.join('/'),pair);
  }
  const fixtures=[...pairs.values()];
  if(fixtures.length!==7 || new Set(fixtures.flat()).size!==14) return null;
  return {week:[...numbers][0],fixtures};
}

async function collectFantasyCalendar(teamHtmls, leagueId, parser, scoreParser=null, currentMatchupDoc=null) {
  const capture = {source:'yahoo_browser_schedule',league_id:leagueId,weeks:[],errors:[],diagnostics:{pages_fetched:0,pages_failed:0,matchup_pages_with_dated_evidence:0,rejected_wrong_week_or_team:0,date_conflicts:0,weeks_attempted:0,complete_weeks:0}};
  const diagnostics=capture.diagnostics, basePath=`/nba/${leagueId}`, origin=location.origin, started=performance.now();
  const docs=teamHtmls.map((html,i)=>({doc:parser.parseFromString(html || '', 'text/html'),owner:String(i+1)}));
  function localURL(href) {
    try { const url=new URL(href,origin); return url.origin===origin && (url.pathname===basePath || url.pathname.startsWith(basePath+'/')) ? url : null; }
    catch (_) { return null; }
  }
  const links=doc=>Array.from(doc.querySelectorAll('a[href]')).map(a=>localURL(a.getAttribute('href'))).filter(Boolean);
  function issue(message) { if (capture.errors.length<12 && !capture.errors.includes(message)) capture.errors.push(message); }
  const budgetAvailable=()=>diagnostics.pages_fetched<60 && performance.now()-started<45000;
  async function read(url) {
    if (!budgetAvailable()) return null;
    diagnostics.pages_fetched++;
    const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),8000);
    try {
      const response=await fetch(url,{credentials:'same-origin',cache:'no-store',signal:controller.signal});
      if (response.ok) return parser.parseFromString(await response.text(),'text/html');
    } catch (_) { /* Previously confirmed observations keep their timestamps. */ }
    finally { clearTimeout(timeout); }
    diagnostics.pages_failed++; return null;
  }
  const home=await read(new URL(basePath,origin).href);
  if (home) docs.push({doc:home,owner:null});
  const settingsURL=docs.flatMap(({doc})=>links(doc)).find(url=>/\/settings\/?$/.test(url.pathname));
  const settings=settingsURL && await read(settingsURL.href);
  if (settings) for (const row of settings.querySelectorAll('tr')) {
    const cells=Array.from(row.querySelectorAll('th,td')).map(el=>(el.textContent || '').trim());
    if (/^Playoffs:?$/i.test(cells[0] || '')) {
      const match=cells.slice(1).join(' ').match(/\bWeek\s+(\d+)/i);
      if (match) capture.regular_season_end_week=Number(match[1])-1;
    }
  }
  if (typeof document !== 'undefined' && location.pathname.startsWith(basePath)) docs.push({doc:document,owner:null});
  const seedURL=docs.flatMap(({doc})=>links(doc)).find(url=>url.pathname===`${basePath}/matchup` && !url.searchParams.has('week')) || new URL(`${basePath}/matchup`,origin);
  if (!seedURL) { issue('Current Yahoo matchup link was not found.'); return capture; }
  // Reuse the freshly fetched, date-verified score document. The generic
  // endpoint can still return last week during Yahoo's Monday rollover.
  const seedDoc=currentMatchupDoc || await read(seedURL.href), seed=seedDoc && readYahooMatchupEvidence(seedDoc,leagueId,origin);
  if (!seed) { issue('Current Yahoo matchup lacks a verified week label and contiguous dated daily links.'); return capture; }
  capture.season=seed.season; capture.current_week=seed.week;
  capture.stage5=home ? parseYahooStage5Page(home,leagueId,origin,seed.week) : {source:'yahoo_browser_league',league_id:leagueId,pending_offers:{scan_complete:false,reason:'League page unavailable'}};
  // One optional GET discovered from Yahoo itself; no propose/accept/reject action.
  const offerURL=docs.flatMap(({doc})=>links(doc)).find(url=>/pending_trade|viewtrade|tradeoffers|pendingtrades/i.test(url.pathname+url.search) && !/propose|accept|reject|cancel/i.test(url.pathname+url.search));
  if(offerURL) {
    const offerDoc=await read(offerURL.href);
    if(offerDoc) capture.stage5.pending_offers=parseYahooStage5Page(offerDoc,leagueId,origin,seed.week).pending_offers;
  }
  capture.season_evidence='Yahoo dated matchup navigation; league display name ignored';
  if (!Number.isInteger(capture.regular_season_end_week) || capture.regular_season_end_week<seed.week || capture.regular_season_end_week>60) {
    issue('Explicit Yahoo normal-season boundary was not found.'); return capture;
  }
  const owners=docs.filter(row=>row.owner).map(row=>row.owner), knownTeams=new Set(owners), byWeek=new Map();
  function accept(row,requestedWeek,requestedTeam) {
    if (!row || row.week!==requestedWeek || !row.pair.includes(requestedTeam) || !row.pair.every(team=>knownTeams.has(team)) || row.season!==capture.season) {
      diagnostics.rejected_wrong_week_or_team++; return false;
    }
    diagnostics.matchup_pages_with_dated_evidence++;
    if (!byWeek.has(row.week)) byWeek.set(row.week,{start:row.start,end:row.end,pairs:new Map(),seen:new Set(),conflict:false});
    const bucket=byWeek.get(row.week), key=row.pair.join('/');
    if (bucket.start!==row.start || bucket.end!==row.end) { bucket.conflict=true; diagnostics.date_conflicts++; return false; }
    for (const existing of bucket.pairs.values()) if (existing.some(team=>row.pair.includes(team)) && existing.join('/')!==key) { bucket.conflict=true; return false; }
    bucket.pairs.set(key,row.pair); row.pair.forEach(team=>bucket.seen.add(team)); return true;
  }
  accept(seed,seed.week,seed.pair[0]);
  // Use the observed Yahoo navigation shape with known provider team IDs.
  // Each requested team's opponent and period still have to come back in HTML.
  const template=links(seedDoc).find(url=>url.pathname===`${basePath}/matchup` && url.searchParams.get('mid1') && url.searchParams.get('week'));
  if (!template) { issue('Yahoo matchup navigation URL template was not found.'); return capture; }
  // The observed League week endpoint remains usable when Yahoo omits its
  // navigation link from server HTML. Response week/card evidence is still mandatory.
  const leagueTemplate=docs.flatMap(({doc})=>links(doc)).find(url=>url.pathname===basePath && url.searchParams.has('matchup_week') && url.searchParams.get('module')==='matchups') || new URL(`${basePath}?matchup_week=${seed.week}&module=matchups&lhst=matchups`,origin);
  // Read season schedules once per team, then one dated matchup per week.
  // Never fan out into seven matchup pages for every scoring period.
  const scheduleRows=new Map(), scheduleURLs=new Map();
  function ingestSchedule(doc,owner) {
    // Yahoo's Schedule tab uses scmid for the selected team. When it is
    // absent, recurring explicit matchup IDs can establish the table owner.
    if (!owner) {
      const evidence=Array.from(doc.querySelectorAll('tr')).flatMap(row=>links(row)).filter(url=>url.searchParams.get('mid1') && url.searchParams.get('mid2'));
      if(evidence.length>=2) {
        let common=new Set([evidence[0].searchParams.get('mid1'),evidence[0].searchParams.get('mid2')]);
        for(const url of evidence.slice(1)) common=new Set([...common].filter(team=>[url.searchParams.get('mid1'),url.searchParams.get('mid2')].includes(team)));
        if(common.size===1) owner=[...common][0];
      }
    }
    for (const row of doc.querySelectorAll('tr')) {
      const cells=Array.from(row.querySelectorAll('th,td'));
      const weekCell=cells.slice(0,2).find(cell=>/^\d+$/.test((cell.textContent || '').trim()));
      const number=Number((weekCell?.textContent || '').trim());
      if (!Number.isInteger(number) || number<seed.week || number>capture.regular_season_end_week) continue;
      for (const url of links(row)) {
        let a=url.searchParams.get('mid1') || owner, b=url.searchParams.get('mid2');
        if (!b) b=url.pathname.match(new RegExp(`^${basePath}/(\\d+)(?:/|$)`))?.[1];
        if (!knownTeams.has(a) || !knownTeams.has(b) || a===b) continue;
        if (!scheduleRows.has(number)) scheduleRows.set(number,new Map());
        const pairs=scheduleRows.get(number), pair=[a,b].sort((x,y)=>Number(x)-Number(y));
        pairs.set(pair.join('/'),pair);
      }
    }
    for (const url of links(doc)) {
      const team=url.searchParams.get('scmid') || url.searchParams.get('team') || url.searchParams.get('team_id') || url.searchParams.get('mid1');
      if (knownTeams.has(team) && /sched/i.test(url.href)) scheduleURLs.set(team,url.href);
    }
  }
  for (const {doc,owner} of docs) ingestSchedule(doc,owner);
  // Follow Yahoo's actual Schedule navigation URL; preserve its query shape.
  function ingestLeague(doc,number) {
    const evidence=readYahooLeagueWeek(doc,leagueId,origin);
    if(!evidence || evidence.week!==number) return false;
    if(!scheduleRows.has(number)) scheduleRows.set(number,new Map());
    for(const pair of evidence.fixtures) if(pair.every(team=>knownTeams.has(team))) scheduleRows.get(number).set(pair.join('/'),pair);
    return true;
  }
  if(home) ingestLeague(home,seed.week);
  function ingestMatchupLinks(doc,number) {
    // The weekly Matchup page can expose all league pairs in its navigation.
    // Only explicitly week-qualified provider IDs count as evidence.
    for(const url of links(doc)) {
      if(url.pathname!==`${basePath}/matchup` || Number(url.searchParams.get('week'))!==number) continue;
      const a=url.searchParams.get('mid1'), b=url.searchParams.get('mid2');
      if(!knownTeams.has(a) || !knownTeams.has(b) || a===b) continue;
      if(!scheduleRows.has(number)) scheduleRows.set(number,new Map());
      const pair=[a,b].sort((x,y)=>Number(x)-Number(y));scheduleRows.get(number).set(pair.join('/'),pair);
    }
  }
  ingestMatchupLinks(seedDoc,seed.week);
  for (let week=seed.week;week<=capture.regular_season_end_week && budgetAvailable();week++) {
    const previous=(typeof cachedYahooFantasyWeeks==='undefined' ? [] : cachedYahooFantasyWeeks).find(row=>row.week===week && row.season===capture.season && row.league_id===String(leagueId));
    if (week!==seed.week && previous && Date.now()-Date.parse(previous.captured_at)<6*86400000 && Date.now()>=Date.parse(previous.captured_at)) continue;
    diagnostics.weeks_attempted++;
    let dated=week===seed.week ? seed : null;
    if (!dated) {
      const url=new URL(template.href);url.searchParams.set('week',String(week));url.searchParams.set('mid1',seed.pair[0]);url.searchParams.delete('mid2');url.searchParams.delete('date');
      const doc=await read(url.href); dated=doc && readYahooMatchupEvidence(doc,leagueId,origin);
      if(doc && dated && dated.week===week) {ingestSchedule(doc,null);ingestMatchupLinks(doc,week);}
    }
    const existing=scheduleRows.get(week);
    if((!existing || existing.size!==7) && leagueTemplate) {
      const url=new URL(leagueTemplate.href);url.searchParams.set('matchup_week',String(week));
      const leagueDoc=await read(url.href);
      if(leagueDoc) ingestLeague(leagueDoc,week);
    }
    const pairs=scheduleRows.get(week);
    if (!pairs || pairs.size!==7 || new Set(Array.from(pairs.values()).flat()).size!==14) {
      issue(`Week ${week}: ${pairs?.size || 0}/7 explicit league fixtures found in Schedule/Matchup HTML; no opponents were inferred.`);
      continue;
    }
    if (dated && dated.week===week && dated.season===capture.season && pairs.has(dated.pair.join('/'))) {
      for (const pair of pairs.values()) accept({...dated,pair},week,pair[0]);
    }
    const bucket=byWeek.get(week);
    if (!bucket || bucket.conflict || bucket.pairs.size!==7 || bucket.seen.size!==14) {
      issue(`Week ${week}: complete dated 14-team coverage could not be verified.`);
      if (week===seed.week) break;
      continue;
    }
    capture.weeks.push({week,start:bucket.start,end:bucket.end,fixtures:Array.from(bucket.pairs.values()).sort((a,b)=>Number(a[0])-Number(b[0]))});
  }
  diagnostics.complete_weeks=capture.weeks.length;
  // Current raw score coverage is needed for qualification, not for the
  // calendar itself. Read at most six extra pages only for a verified offer.
  const currentPairs=byWeek.get(seed.week);
  if(typeof scoreParser==='function' && capture.stage5?.standings && capture.stage5.pending_offers?.scan_complete && capture.stage5.pending_offers.offers?.length && currentPairs?.pairs.size===7 && !currentPairs.conflict) {
    const fields=['FGM','FGA','FTM','FTA','FG3M','PTS','REB','AST','STL','BLK','TOV'];
    const validScore=(value,pair)=>value && [value.team_a,value.team_b].every(team=>team && fields.every(field=>Number.isFinite(team[field]))) && [value.team_a.yahoo_team_id,value.team_b.yahoo_team_id].map(String).sort((a,b)=>Number(a)-Number(b)).join('/')===pair.join('/') && value.week===seed.week;
    const pairs=Array.from(currentPairs.pairs.values()), boards=[];
    for(let offset=0;offset<pairs.length && budgetAvailable();offset+=2) {
      const rows=await Promise.all(pairs.slice(offset,offset+2).map(async pair=>{
        let score;
        try {
          if(pair.join('/')===seed.pair.join('/')) score=scoreParser(seedDoc);
          else {
            const url=new URL(template.href);url.searchParams.set('week',String(seed.week));url.searchParams.set('mid1',pair[0]);url.searchParams.set('mid2',pair[1]);url.searchParams.delete('date');
            const doc=await read(url.href);if(doc) score=scoreParser(doc);
          }
        } catch (_) { return null; }
        return validScore(score,pair) ? [score.team_a,score.team_b].map(team=>({...team,slot:team.yahoo_team_id})) : null;
      }));
      boards.push(...rows.filter(Boolean));
    }
    if(boards.length===7) capture.stage5.current_scoreboard={week:seed.week,week_verified:true,matchups:boards,matchup_states:boards.map(()=>({week_start:seed.start,week_end:seed.end}))};
  }
  if (!budgetAvailable()) issue('Fantasy capture reached its page/time budget; partial confirmed weeks retained.');
  return capture;
}

if (typeof module==='object') module.exports={parseYahooFantasyPeriod,parseYahooDatedMatchup,readYahooMatchupEvidence,readYahooLeagueWeek,parseYahooStage5Page,collectFantasyCalendar};
