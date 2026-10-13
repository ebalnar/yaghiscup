"""Build static NHL game-log snapshots for GitHub Pages (Python stdlib only)."""
import datetime as dt
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEASON = '20262027'
ROSTERS = json.loads((ROOT / 'rosters.json').read_text())
PINS = json.loads((ROOT / 'player-ids.json').read_text())
OUT = ROOT / 'data' / 'stats.json'
HEADERS = {'User-Agent': 'YaghisCup/1.0 (unofficial fantasy tracker)', 'Accept': 'application/json'}

def fetch(url):
    error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=25) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            error = exc
            time.sleep(attempt + 1)
    raise RuntimeError(str(error))

def norm(s):
    import unicodedata
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in s).split())

def month_index(date):
    try: d = dt.date.fromisoformat(date[:10])
    except (TypeError, ValueError): return -1
    if d.year == 2026 and d.month in (9, 10): return 0
    if d.year == 2026 and d.month in (11, 12): return d.month - 10
    if d.year == 2027 and 1 <= d.month <= 4: return d.month + 2
    return -1

def directory():
    people = {}
    for kind in ('skater', 'goalie'):
        url = f'https://api.nhle.com/stats/rest/en/{kind}/summary?isAggregate=false&isGame=false&start=0&limit=3000&cayenneExp=' + urllib.parse.quote(f'seasonId={SEASON} and gameTypeId=2')
        try:
            for p in fetch(url).get('data', []):
                name = p.get('skaterFullName') or p.get('goalieFullName') or p.get('playerName')
                if name and p.get('playerId'): people[norm(name)] = (p['playerId'], p.get('teamAbbrevs', ''))
        except Exception as e: print('Directory report unavailable:', e)
    teams = 'ANA BOS BUF CAR CBJ CGY CHI COL DAL DET EDM FLA LAK MIN MTL NJD NSH NYI NYR OTT PHI PIT SEA SJS STL TBL TOR UTA VAN VGK WPG WSH'.split()
    for team in teams:
        try:
            j = fetch(f'https://api-web.nhle.com/v1/roster/{team}/current')
            for p in j.get('forwards', []) + j.get('defensemen', []) + j.get('goalies', []):
                name = p.get('firstName', {}).get('default', '') + ' ' + p.get('lastName', {}).get('default', '')
                people[norm(name)] = (p['id'], team)
        except Exception as e: print('Roster unavailable', team, e)
    return people

def find_player(name, people):
    if name in PINS: return PINS[name], ''
    key = norm(name)
    if key in people: return people[key]
    matches = [v for k, v in people.items() if k.split()[-1:] == key.split()[-1:] and k.split()[:1] == key.split()[:1]]
    return matches[0] if len(matches) == 1 else (None, '')

def number(game, *keys):
    for key in keys:
        if game.get(key) is not None:
            try: return float(game[key])
            except (ValueError, TypeError): pass
    return None

def hits_report(player_id):
    expr = urllib.parse.quote(f'seasonId={SEASON} and gameTypeId=2 and playerId={player_id}')
    url = f'https://api.nhle.com/stats/rest/en/skater/realtime?isAggregate=false&isGame=true&start=0&limit=200&cayenneExp={expr}'
    rows = fetch(url).get('data')
    if rows is None: raise ValueError('Hits report missing data')
    return {str(row['gameId']): row['hits'] for row in rows if row.get('gameId') is not None and row.get('hits') is not None}

def goalie_report(player_id):
    """Get per-game goalie shot totals from the NHL stats reports endpoint."""
    expr = urllib.parse.quote(f'seasonId={SEASON} and gameTypeId=2 and playerId={player_id}')
    url = (f'https://api.nhle.com/stats/rest/en/goalie/summary?'
           f'isAggregate=false&isGame=true&start=0&limit=200&cayenneExp={expr}')
    rows = fetch(url).get('data')
    if not isinstance(rows, list):
        raise ValueError('Goalie summary report missing data')
    return {str(row['gameId']): row for row in rows if row.get('gameId') is not None}

def main():
    people = directory()
    players, missing = [], []
    for team, positions in ROSTERS.items():
        for position, names in positions.items():
            for name in names:
                pid, club = find_player(name, people)
                issues = []
                months = [{} for _ in range(7)]
                if not pid:
                    missing.append(name)
                    issues.append('NHL player ID not resolved; add an ID to player-ids.json')
                else:
                    try:
                        logs = fetch(f'https://api-web.nhle.com/v1/player/{pid}/game-log/{SEASON}/2')
                        games = logs.get('gameLog', logs.get('games', []))
                        if not isinstance(games, list): raise ValueError('Unexpected game log structure')
                    except Exception as e:
                        games = []
                        issues.append('Game log unavailable: ' + str(e))
                    goalie_games = {}
                    if position == 'G':
                        try:
                            goalie_games = goalie_report(pid)
                        except Exception as e:
                            issues.append('Goalie summary report unavailable: ' + str(e))
                    hits = {}
                    if position != 'G' and games:
                        try: hits = hits_report(pid)
                        except Exception as e: issues.append('Hits report unavailable: ' + str(e))
                    for g in games:
                        m = month_index(g.get('gameDate') or g.get('date'))
                        if m < 0: continue
                        vals = {}
                        if position == 'G':
                            # NHL goalie game logs may expose a save percentage
                            # without an explicit saves count.
                            report = goalie_games.get(str(g.get('gameId')), {})
                            shots = number(g, 'shotsAgainst', 'shotsAgainstTotal', 'shots')
                            saves = number(g, 'saves', 'savesTotal')
                            goals_against = number(g, 'goalsAgainst', 'goalsAgainstTotal')
                            pct = number(g, 'savePctg', 'savePct', 'savePercentage')
                            if pct is not None and pct > 1:
                                pct /= 100.0
                            # The NHL web game-log often omits shots/saves entirely.
                            # The per-game NHL goalie summary report provides them.
                            if shots is None:
                                shots = number(report, 'shotsAgainst', 'shotsAgainstTotal')
                            if saves is None:
                                saves = number(report, 'saves', 'savesTotal')
                            if goals_against is None:
                                goals_against = number(report, 'goalsAgainst')
                            if pct is None:
                                pct = number(report, 'savePct', 'savePctg', 'savePercentage')
                                if pct is not None and pct > 1:
                                    pct /= 100.0
                            if shots is None and saves is not None and goals_against is not None:
                                shots = saves + goals_against
                            if saves is None and shots is not None and goals_against is not None:
                                saves = shots - goals_against
                            if saves is None and shots is not None and pct is not None:
                                saves = round(shots * pct)
                            if shots is None or saves is None or shots < 0 or saves < 0 or saves > shots:
                                issues.append('Goalie saves/shots unavailable for ' + str(g.get('gameDate')))
                            else:
                                vals.update(shots=shots, saves=saves)
                            decision = str(g.get('decision', '')).upper()
                            vals['wins'] = 1 if decision in ('W', 'WIN') else 0
                            shutouts = number(g, 'shutouts')
                            if shutouts is None:
                                ga = number(g, 'goalsAgainst')
                                shutouts = 1 if decision in ('W', 'WIN') and ga == 0 and shots and shots > 0 else 0
                            vals['shutouts'] = shutouts
                        else:
                            for dest, keys in [('goals', ('goals',)), ('assists', ('assists',)), ('ppp', ('powerPlayPoints', 'powerPlayPts')), ('gwg', ('gameWinningGoals', 'gameWinningGoal'))]:
                                value = number(g, *keys)
                                if value is None: issues.append(dest + ' missing for ' + str(g.get('gameDate')))
                                else: vals[dest] = value
                            hit = number(g, 'hits')
                            if hit is None: hit = hits.get(str(g.get('gameId')))
                            if hit is None: issues.append('Hits missing for ' + str(g.get('gameDate')))
                            else: vals['hits'] = float(hit)
                        for key, val in vals.items(): months[m][key] = months[m].get(key, 0) + val
                players.append({'team': team, 'position': position, 'name': name, 'nhlTeam': club, 'id': pid, 'unresolved': not bool(pid), 'months': months, 'issues': sorted(set(issues))})
    today = dt.datetime.now(dt.timezone.utc).date()
    ends = [dt.date(2026,10,31), dt.date(2026,11,30), dt.date(2026,12,31), dt.date(2027,1,31), dt.date(2027,2,28), dt.date(2027,3,31), dt.date(2027,4,30)]
    # Do not award championship points for an unfinished month.
    completed = max((i for i, end in enumerate(ends) if today > end), default=-1)
    result = {'season': SEASON, 'updatedAt': dt.datetime.now(dt.timezone.utc).isoformat(), 'completedThrough': completed, 'roster': ROSTERS, 'players': players, 'missing': missing}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + '\n')
    print('Wrote', OUT, 'players:', len(players), 'unmatched:', len(missing), 'with warnings:', sum(bool(p['issues']) for p in players))

if __name__ == '__main__': main()
