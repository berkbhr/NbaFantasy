const {test} = require('node:test');
const assert = require('node:assert/strict');
const {parseYahooDatedMatchup: evidence, collectFantasyCalendar} = require('../src/yahoo_fixtures.js');
const {readYahooLeagueWeek}=require('../src/yahoo_fixtures.js');
const origin='https://basketball.fantasysports.yahoo.com';
const href=(week,date,a=14,b=2)=>`${origin}/nba/64691/matchup?week=${week}&date=${date}&mid1=${a}&mid2=${b}`;
function dates(start,count=7) { return Array.from({length:count},(_,i)=>new Date(Date.parse(start+'T00:00:00Z')+i*86400000).toISOString().slice(0,10)); }

// These URL shapes and the custom #matchup_selectlist_nav Week 2 label were
// observed in the actual Yahoo UI. This is parser evidence, not a saved league calendar.
test('custom Yahoo week control and explicit daily links identify current Week 2',()=>{
  const row=evidence(dates('2026-10-26').map(d=>href(2,d)),'Week 2','64691',origin);
  assert.equal(row.week,2); assert.equal(row.season,'2026_27');
  assert.deepEqual(row.pair,['2','14']);
  assert.equal(row.start,'2026-10-26'); assert.equal(row.end,'2026-11-01');
});
test('actual observed Week 3 pair14 versus6 is read from provider URLs',()=>{
  const row=evidence(dates('2026-11-02').map(d=>href(3,d,14,6)),'Week 3','64691',origin);
  assert.deepEqual(row.pair,['6','14']); assert.equal(row.end,'2026-11-08');
});
test('two-week period uses every actual dated link instead of assuming seven days',()=>{
  const row=evidence(dates('2027-02-08',14).map(d=>href(17,d)),'Week 17','64691',origin);
  assert.equal(row.end,'2027-02-21'); assert.equal(row.dates.length,14);
});
test('mixed opponents, wrong week/league/origin and incomplete daily navigation are rejected',()=>{
  const good=dates('2026-10-26').map(d=>href(2,d));
  assert.equal(evidence(good,'Week 3','64691',origin),null);
  assert.equal(evidence(good,'Week 2','12345',origin),null);
  assert.equal(evidence(good,'Week 2','64691','https://other.example'),null);
  assert.equal(evidence([good[0],good[2]],'Week 2','64691',origin),null);
  assert.equal(evidence([good[0]],'Week 2','64691',origin),null);
  assert.equal(evidence([...good,href(2,'2026-10-26',14,6)],'Week 2','64691',origin),null);
});

const anchor=url=>({getAttribute:name=>name==='href'?url:null});
function doc({links=[],week=null,settings=false,rows=[],leaguePairs=null}) {
  return {
    querySelector:query=>query==='#matchupweek' && leaguePairs ? {textContent:`Week ${week} Matchups`,querySelectorAll:()=>leaguePairs.map(pair=>({querySelectorAll:()=>pair.map(team=>anchor(`${origin}/nba/64691/${team}`))}))} : query==='#matchup_selectlist_nav' && week ? {textContent:`Week ${week}`,getAttribute:name=>name==='aria-label'?`Week ${week}`:null} : null,
    querySelectorAll:query=>{
      if(query==='a[href]') return links.map(anchor);
      if(query==='tr' && settings) return [{querySelectorAll:()=>[{textContent:'Playoffs'},{textContent:'8 teams - Week 7, 8 and 9'}]}];
      if(query==='tr') return rows;
      return [];
    },
  };
}
async function captureFixture(wrongWeek=false,scheduleTables=true,leagueCards=false,omitLeagueNavigation=false,anchored=false) {
  const saved={fetch:global.fetch,location:global.location};
  const rows=[];
  for(let week=2;week<=6;week++) {
    const pairs=[['14',week===3?'6':'2']];
    const rest=Array.from({length:14},(_,i)=>String(i+1)).filter(t=>!pairs[0].includes(t));
    while(rest.length) pairs.push([rest.shift(),rest.shift()]);
    for(const [a,b] of pairs) rows.push({querySelectorAll:query=>query==='th,td' ? [{textContent:String(week)}] : query==='a[href]' ? [anchor(href(week,'2026-11-02',a,b))] : []});
  }
  const teamDoc=doc({links:[`${origin}/nba/64691/settings`,`${origin}/nba/64691/matchup`,...(omitLeagueNavigation ? [] : [`${origin}/nba/64691?matchup_week=3&module=matchups&lhst=matchups`])],rows:scheduleTables ? rows : []});
  const docs=new Map([['team',teamDoc],['home',teamDoc],['settings',doc({settings:true})]]);
  let token=0;
  const allTeams=Array.from({length:14},(_,i)=>String(i+1));
  global.location={origin};
  global.fetch=async input=>{
    const url=new URL(input);
    let result;
    if(url.pathname.endsWith('/settings')) result=docs.get('settings');
    else if(url.pathname==='/nba/64691' && !url.searchParams.has('matchup_week')) result=docs.get('home');
    else {
      let week=Number(url.searchParams.get('matchup_week') || url.searchParams.get('week') || 2);
      if(wrongWeek && week===4) week=3;
      const start=new Date(Date.parse('2026-10-26T00:00:00Z')+(week-2)*7*86400000).toISOString().slice(0,10);
      const pairs=[['14',week===3?'6':'2']];
      const rest=allTeams.filter(t=>!pairs[0].includes(t));
      while(rest.length) pairs.push([rest.shift(),rest.shift()]);
      const team=url.searchParams.get('mid1') || '14';
      const pair=pairs.find(p=>p.includes(team));
      const nav=dates(start).map(d=>href(week,d,...pair));
      if(!leagueCards) for(const [a,b] of pairs) nav.push(`${origin}/nba/64691/matchup?week=${week}&mid1=${a}&mid2=${b}`);
      nav.push(`${origin}/nba/64691/matchup?week=${week+1}&module=matchup&mid1=${team}`);
      result=doc({week,links:nav,leaguePairs:leagueCards && url.searchParams.has('matchup_week') ? pairs : null});
    }
    const key=`response-${token++}`; docs.set(key,result);
    return {ok:true,text:async()=>key};
  };
  const currentDoc=anchored ? doc({week:3,links:dates('2026-11-02').map(d=>href(3,d,14,6))}) : null;
  try { return await collectFantasyCalendar(Array(14).fill('team'),'64691',{parseFromString:text=>docs.get(text)},null,currentDoc); }
  finally { global.fetch=saved.fetch; global.location=saved.location; }
}
test('season tables avoid per-team per-week matchup requests',async()=>{
  const capture=await captureFixture();
  assert.equal(capture.current_week,2); assert.equal(capture.regular_season_end_week,6);
  assert.deepEqual(capture.weeks.map(w=>w.week),[2,3,4,5,6]);
  for(const week of capture.weeks) { assert.equal(week.fixtures.length,7); assert.equal(new Set(week.fixtures.flat()).size,14); }
  assert.ok(capture.diagnostics.pages_fetched<=8); // home/settings/seed plus one dated page per future week.
  assert.equal(capture.diagnostics.complete_weeks,5);
});
test('a cached wrong-week response never becomes a fabricated requested fixture',async()=>{
  const capture=await captureFixture(true);
  assert.ok(!capture.weeks.some(w=>w.week===4));
  assert.ok(capture.errors.some(e=>e.includes('Week 4')));
});
test('missing Schedule tables still use one weekly page for all explicit league pairs',async()=>{
  const capture=await captureFixture(false,false);
  assert.deepEqual(capture.weeks.map(w=>w.week),[2,3,4,5,6]);
  assert.ok(capture.diagnostics.pages_fetched<=8);
  for(const week of capture.weeks) assert.equal(new Set(week.fixtures.flat()).size,14);
});
test('reported 1-of-7 failure is repaired via the observed League week endpoint',async()=>{
  const capture=await captureFixture(false,false,true);
  assert.deepEqual(capture.weeks.map(w=>w.week),[2,3,4,5,6]);
  assert.ok(capture.diagnostics.pages_fetched<=13);
  for(const week of capture.weeks) assert.equal(new Set(week.fixtures.flat()).size,14);
});
test('missing server-rendered League navigation does not skip League requests',async()=>{
  const capture=await captureFixture(false,false,true,true);
  assert.deepEqual(capture.weeks.map(w=>w.week),[2,3,4,5,6]);
  assert.ok(capture.diagnostics.pages_fetched<=13);
});

// Observed live Yahoo structure: #matchupweek -> list -> li, with two
// /nba/{league}/{team} links per card (duplicate logo/name links allowed).
test('actual League card structure yields seven pairs without mid1/mid2 URLs',()=>{
  const pairs=[['14','2'],['1','8'],['3','12'],['4','10'],['5','11'],['6','7'],['9','13']];
  const root={textContent:'Matchups Week 2 Week 2 Matchups In progress',querySelectorAll:()=>pairs.map(pair=>({querySelectorAll:()=>pair.flatMap(team=>[anchor(`${origin}/nba/64691/${team}`),anchor(`${origin}/nba/64691/${team}`)])}))};
  const page={querySelector:selector=>selector==='#matchupweek'?root:null};
  const value=readYahooLeagueWeek(page,'64691',origin);
  assert.equal(value.week,2);assert.equal(value.fixtures.length,7);assert.equal(new Set(value.fixtures.flat()).size,14);
  assert.equal(readYahooLeagueWeek(page,'12345',origin),null);
  pairs[6]=pairs[0];assert.equal(readYahooLeagueWeek(page,'64691',origin),null);
});
const fs = require('node:fs');
const vm = require('node:vm');
const bridge = fs.readFileSync(require('node:path').join(__dirname, '../src/yahoo_browser_sync.py'), 'utf8');
const parserCode = bridge.slice(bridge.indexOf('    function parseMatchupDoc(doc)'), bridge.indexOf('    function parseTransactionsDoc(doc)'));
function parseScore(played, cells) {
  const link={textContent:'Example',getAttribute:()=>'/nba/64691/14'};
  const second={textContent:'Opponent',getAttribute:()=>'/nba/64691/6'};
  const row=(a)=>({querySelectorAll:q=>q==='th, td'?cells.map(textContent=>({textContent})):q==='td, th'?Array(12).fill({}):[a],querySelector:()=>a});
  const table={querySelectorAll:q=>q.startsWith('thead')?['PTS','REB','AST'].map(textContent=>({textContent})): [row(link),row(second)]};
  const doc={body:{textContent:`44 Remaining ${played}/44 Games Played ${played}/38 Remaining 38`},querySelectorAll:()=>[table]};
  const context=vm.createContext({leagueId:'64691', location:{origin}, URL, readYahooMatchupEvidence:()=>({week:3,start:'2026-11-02',end:'2026-11-08'})});
  vm.runInContext(parserCode,context); context.doc=doc;
  return vm.runInContext('parseMatchupDoc(doc)',context);
}
test('observed Week 3 dash scoreboard is zero only before any games played',()=>{
  const values=['Example','-/-','-','-/-','-','-','-','-','-','-','-','0'];
  const score=parseScore(0,values);
  assert.equal(score.week,3); assert.equal(score.period_start,'2026-11-02');
  assert.equal(score.team_a.games_remaining,44);
  for(const side of ['team_a','team_b'])for(const key of ['FGM','FGA','FTM','FTA','FG3M','PTS','REB','AST','STL','BLK','TOV']) assert.equal(score[side][key],0);
  const started=parseScore(1,values);
  assert.ok(!Number.isFinite(started.team_a.PTS));
});
test('malformed and missing fractions never become a fabricated zero score',()=>{
  assert.equal(parseScore(0,['Example','','-','','-','-','-','-','-','-','-','0']),null);
});
test('Monday capture rejects prior and future scoring periods even with valid numbers',()=>{
 const source=bridge.slice(bridge.indexOf('    function matchupReady(value)'),bridge.indexOf('    async function renderedMatchup'));
 const context=vm.createContext({});vm.runInContext(source,context);
 context.score=parseScore(0,['Example','-/-','-','-/-','-','-','-','-','-','-','-','0']);
 assert.equal(vm.runInContext("matchupCoversDate(score,'2026-11-02')",context),true);
 assert.equal(vm.runInContext("matchupCoversDate(score,'2026-11-01')",context),false);
 assert.equal(vm.runInContext("matchupCoversDate(score,'2026-11-09')",context),false);
});
test('fresh Week 3 scoreboard anchors calendar when generic endpoint still serves Week 2',async()=>{
 const capture=await captureFixture(false,true,false,false,true);
 assert.equal(capture.current_week,3);
 assert.ok(capture.weeks.some(w=>w.week===3 && w.fixtures.some(pair=>pair.includes('14') && pair.includes('6'))));
});
