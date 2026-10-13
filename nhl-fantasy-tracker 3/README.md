# Yaghi’s Cup — 2026–27 NHL Fantasy Tracker

**Preview on your computer before publishing:**

1. Install Node.js 20+ from https://nodejs.org
2. Unzip this project. Open Terminal in the `nhl-fantasy-tracker` folder.
3. Run `npm start`.
4. Visit **http://localhost:3000** in your browser.
5. Keep Terminal running while previewing. Ctrl+C stops the site.

**Public hosting:** Upload the entire folder to GitHub and deploy a Node Web Service on Render. Start command: `npm start`. Hosting must support Node, not static-only GitHub Pages.

**Stats:** NHL player game logs (regular season, 20262027) plus NHL skater realtime report for hits. Player resolution uses NHL stats season directory and current team rosters. The first request can take time. Server caches data for six hours; Refresh button forces a new fetch. NHL public endpoints are undocumented and may change. Player IDs can be pinned in `player-ids.json` as `{ "Player Name": 1234567 }`.

**Important:** Data-quality warnings identify players or stats that could not be verified. Do not treat incomplete results as official championship standings. The daily update is *on visit* rather than an independently scheduled background task; the host may sleep when idle. For a guaranteed daily update, add a scheduled job or external uptime trigger.

# McPuckface Fantasy Hockey Championship

A Node.js 20+ website with a plain HTML/CSS/JS dashboard and NHL API-backed daily statistics.

## Run locally

```bash
npm start
```

Open http://localhost:3000.

## Publish for free (Render)

1. Create a GitHub repository and upload `server.js`, `rosters.json`, `package.json` and the `public` folder (all at the repository root).
2. At https://render.com choose **New > Web Service**, connect your GitHub repository.
3. Set Runtime **Node**, Build Command `npm install`, Start Command `npm start`, choose an available free tier if offered.
4. Deploy, then share the Render URL. The first visit after idle may take a while.

## Data and scoring

The backend discovers players through NHL season statistical summary endpoints, falling back to current team rosters if needed. It retrieves each player's NHL regular-season game log and sums statistics by game date into Sep/Oct, Nov, Dec, Jan, Feb, Mar, Apr. Save percentage is calculated as **total saves / total shots against**, not the mean of game percentages. Each statistical category awards 2, 1, 0 roto points, splitting points for ties. Monthly roto standings then award 2, 1, 0 championship points, also splitting ties. Backend refreshes after 12 hours when visited; browser refresh alone within 12 hours does not force an NHL refetch.

## Important caveats

- **Verify the NHL game-log response fields** for `hits`, `powerPlayPoints`, `gameWinningGoals`, `shotsAgainst`, `saves`, `wins`, and `shutouts`. The NHL's public API is undocumented and may omit some fields; missing fields currently display as zero, not confirmed zero. A production-grade tracker should supplement game logs with NHL boxscores or the stats REST API for those fields and reconcile results.
- Unmatched players show a warning and zero until found in the NHL directory. Prospects not yet in the NHL may not appear.
- The public NHL API may change or rate-limit requests. This is a fan project, not an NHL-supported service.
- The championship leaderboard includes the current month provisionally and excludes future months. Current-month points can change until the month ends.
- All roster names are editable in `rosters.json` and require redeployment after edits.
