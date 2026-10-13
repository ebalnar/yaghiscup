# Yaghi's Cup — GitHub Pages edition

Static NHL fantasy tracker for 2026–27, with fixed rosters, eight categories, and seven monthly rounds. **No Node.js or server hosting required.**

## Publish

1. Upload **the contents of this ZIP** (not the containing folder) to the root of `ebalnar/yaghiscup`, replacing the older files if prompted. Make sure `.github/workflows/update-nhl.yml` is included.
2. GitHub repository → **Settings → Pages** → Deploy from a branch → `main` → `/ (root)` → Save.
3. GitHub repository → **Actions → Update NHL fantasy statistics → Run workflow** to generate `data/stats.json` for the first time. If GitHub requests permission for Actions to write commits, go to **Settings → Actions → General → Workflow permissions → Read and write permissions**.
4. Visit https://ebalnar.github.io/yaghiscup/ after deployment. The daily job is scheduled for 12:30 UTC; GitHub scheduled jobs can be delayed.

## How updates work

The Python script `scripts/update_stats.py` requests NHL season game logs and a separate hits report, then saves a static snapshot at `data/stats.json`. The site fetches that JSON. The **Refresh** button reloads the most recent published snapshot; it does not run the NHL fetch. Use **Run workflow** for an on-demand NHL refresh.

**Accuracy caveats:** The NHL endpoints are unofficial and may change. The player directory may omit prospects who have never appeared on an NHL roster. Add confirmed NHL player IDs in `player-ids.json` as `{"Full Name": 1234567}`. The website flags unmatched players and unavailable statistics. Some goalie and skater game-log fields may not be available; missing values must be checked before treating scores as final. This build is not yet end-to-end verified against live NHL responses.

Monthly championship points are awarded only for **completed** months. September and October are combined. Ties split roto and championship points. Goalie save percentage is calculated from total saves divided by total shots faced, not averaged game percentages.
