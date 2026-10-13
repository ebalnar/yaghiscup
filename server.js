import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
const PORT=process.env.PORT||3000, SEASON='20262027';
const roster=JSON.parse(await fs.readFile(new URL('./rosters.json',import.meta.url),'utf8'));
const base=new URL('./public/',import.meta.url);
const aliases={'beckett sennecke':'beckett sennecke','matvei michkov':'matvei michkov','axel sandin pellikka':'axel sandin pellikka','zayne parekh':'zayne parekh'};
let cache=null, pending=null;
const TTL=6*3600*1000;
const playerIds=JSON.parse(await fs.readFile(new URL('./player-ids.json',import.meta.url),'utf8'));
async function hitsByGame(id){
 const exp=encodeURIComponent(`seasonId=${SEASON} and gameTypeId=2 and playerId=${id}`);
 const u=`https://api.nhle.com/stats/rest/en/skater/realtime?isAggregate=false&isGame=true&start=0&limit=200&cayenneExp=${exp}`;
 const j=await get(u);if(!Array.isArray(j.data))throw Error('NHL realtime report missing data');
 return new Map(j.data.filter(x=>x.gameId!=null).map(x=>[String(x.gameId),Number(x.hits)]));
}

const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9 ]/g,' ').replace(/\s+/g,' ').trim();
async function get(url){const r=await fetch(url,{headers:{'User-Agent':'FantasyTracker/1.0','Accept':'application/json'},signal:AbortSignal.timeout(18000)});if(!r.ok)throw Error(`${r.status} ${url}`);return r.json()}
async function directory(){
 // NHL stats API provides league-wide player directory for a season; if unavailable, fall back to NHL team rosters.
 const people=new Map();
 for(const kind of ['skater','goalie']){
  try{const u=`https://api.nhle.com/stats/rest/en/${kind}/summary?isAggregate=false&isGame=false&start=0&limit=3000&cayenneExp=${encodeURIComponent(`seasonId=${SEASON} and gameTypeId=2`)}`;const j=await get(u);for(const p of j.data||[])if(p.playerId)people.set(p.playerId,{id:p.playerId,name:p.skaterFullName||p.goaliesFullName||p.playerName||'',team:p.teamAbbrevs||'',kind})}catch(e){console.warn('Stats directory:',e.message)}
 }
 // Rosters capture players without games played yet (where NHL lists them on an NHL roster).
 if(people.size<50){const teams=['ANA','BOS','BUF','CAR','CBJ','CGY','CHI','COL','DAL','DET','EDM','FLA','LAK','MIN','MTL','NJD','NSH','NYI','NYR','OTT','PHI','PIT','SEA','SJS','STL','TBL','TOR','UTA','VAN','VGK','WPG','WSH'];await Promise.all(teams.map(async t=>{try{const j=await get(`https://api-web.nhle.com/v1/roster/${t}/current`);for(const p of [...(j.forwards||[]),...(j.defensemen||[]),...(j.goalies||[])])people.set(p.id,{id:p.id,name:[p.firstName?.default,p.lastName?.default].join(' '),team:t})}catch{}}))}
 return [...people.values()];
}
function locate(name,players){const n=norm(aliases[norm(name)]||name);let p=players.find(x=>norm(x.name)===n);if(!p){const parts=n.split(' ');p=players.find(x=>norm(x.name).split(' ').at(-1)===parts.at(-1)&&norm(x.name).startsWith(parts[0]+' '))}return p}
function monthOf(date){const d=new Date(date+'T12:00:00Z'),m=d.getUTCMonth(),y=d.getUTCFullYear();if(y===2026&&(m===8||m===9))return 0;if(y===2026&&m>=10)return m-9;if(y===2027&&m<=3)return m+3;return -1}
function val(x,...keys){for(const k of keys)if(x?.[k]!=null&&x[k]!=='')return Number(x[k])||0;return 0}
function statsOf(g,goalie){if(goalie){let shots=val(g,'shotsAgainst','shotsAgainstTotal'),saves=val(g,'saves','savesTotal');if(!shots){const pct=val(g,'savePctg','savePercentage');if(pct&&saves)shots=Math.round(saves/pct)}return {shots,saves,wins: g.decision==='W'||g.decision==='WIN'?1:val(g,'wins'),shutouts:val(g,'shutouts')||((g.decision==='W'||g.decision==='WIN')&&val(g,'goalsAgainst')===0&&shots>0?1:0)}}return {goals:val(g,'goals'),assists:val(g,'assists'),hits:val(g,'hits'),ppp:val(g,'powerPlayPoints','powerPlayPts'),gwg:val(g,'gameWinningGoals','gameWinningGoal')};}
async function build(){const people=await directory(),missing=[],players=[];for(const [team,positions] of Object.entries(roster))for(const [position,names] of Object.entries(positions))for(const name of names){const pinned=playerIds[name];const found=pinned?{id:pinned,name,team:''}:locate(name,people);if(!found){missing.push(`${name} (${team})`);players.push({team,position,name,unresolved:true,months:Array.from({length:7},()=>({})),issues:['NHL player ID not found']});continue}let games=[],issues=[];try{const j=await get(`https://api-web.nhle.com/v1/player/${found.id}/game-log/${SEASON}/2`);games=j.gameLog||j.games||[]}catch(e){issues.push('Game log unavailable: '+e.message)}
 let hits=null;if(position!=='G'&&games.length){try{hits=await hitsByGame(found.id)}catch(e){issues.push('Hits report unavailable: '+e.message)}}const months=Array.from({length:7},()=>({}));for(const g of games){const idx=monthOf(g.gameDate||g.date);if(idx<0)continue;const stat=statsOf(g,position==='G');if(position!=='G'){if(g.hits!=null)stat.hits=Number(g.hits);else if(hits?.has(String(g.gameId)))stat.hits=hits.get(String(g.gameId));else {delete stat.hits;issues.push('Hits missing for '+(g.gameDate||'game'))}}
 if(position==='G' && !('shotsAgainst' in g) && !('shotsAgainstTotal' in g))issues.push('Goalie shots missing for '+(g.gameDate||'game'));
 for(const [key,v] of Object.entries(stat))months[idx][key]=(months[idx][key]||0)+v;}players.push({team,position,name,nhlName:found.name,nhlTeam:found.team,id:found.id,months,games:games.length,issues:[...new Set(issues)]});}
return {season:SEASON,updatedAt:new Date().toISOString(),players,missing,roster,warning:missing.length?'Some players could not be matched to NHL records. Their data is incomplete and flagged.':''}}
async function data(){if(cache&&Date.now()-cache.time<TTL)return cache.value;if(!pending)pending=build().then(value=>(cache={time:Date.now(),value},value)).finally(()=>pending=null);return pending}
const types={'.html':'text/html; charset=utf-8','.js':'application/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json'};
http.createServer(async(req,res)=>{try{const url=new URL(req.url,'http://localhost');if(url.pathname==='/api/data'){if(url.searchParams.has('refresh'))cache=null;const d=await data();res.writeHead(200,{'Content-Type':'application/json','Cache-Control':'public, max-age=300'});res.end(JSON.stringify(d));return}const file=url.pathname==='/'?'index.html':url.pathname.slice(1);const full=path.resolve(base.pathname,file);if(!full.startsWith(path.resolve(base.pathname)+path.sep)&&full!==path.resolve(base.pathname,'index.html'))throw Error('Invalid path');const body=await fs.readFile(full);res.writeHead(200,{'Content-Type':types[path.extname(full)]||'application/octet-stream'});res.end(body)}catch(e){res.writeHead(500,{'Content-Type':'application/json'});res.end(JSON.stringify({error:e.message}))}}).listen(PORT,()=>console.log('Tracker listening on '+PORT));
