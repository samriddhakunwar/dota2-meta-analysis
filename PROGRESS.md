# PROGRESS: handoff notes

Day 2 starts here. Day 1 ended on 2026-10-26.

## Source data (as found, not as described)

- The zip is `../archive.zip` (9.23 GB compressed, 48.5 GB uncompressed, 1,546 files).
- **Folders are yearly for 2016–2025 (`2024/`, `2025/`) and monthly only for 2026 (`202601/`–`202609/`)**. Each folder has 11–12 CSVs. We use only `main_metadata.csv` and `picks_bans.csv`. `players.csv` is 0.1–1.7 GB per folder and is not extracted.
- Window used: `START_YEAR = 2024` in `load.py`, covering folders 2024, 2025 and 202601–202609, i.e. 2024-01-01 → 2026-09-13. That's about 85 MB extracted.
- Constants used: `Heroes`, `Patch`, `Leagues`. The whole `Constants/` folder is extracted.

## Final column mapping

| Concept | Raw source | Clean column |
|---|---|---|
| match id | `main_metadata.match_id` / `picks_bans.match_id` (BIGINT) | `match_id` |
| start time | `main_metadata.start_date_time` (TIMESTAMP, UTC) | `start_time`, plus `match_date`, `match_month`, `match_year` |
| patch | `main_metadata.patch` = **0-based row position** in `Constants.Patch.csv` (54 = 7.35 … 60 = 7.41). The patch file has no id column. | `patch_id`, `patch_name` (VARCHAR; must not be read as DOUBLE, or "7.40" becomes 7.4), `patch_id_original` |
| patch release | `Constants.Patch.date` (ISO UTC string) | `patches.release_time` |
| league | `leagueid` → `Constants.Leagues.leaguename`, `tier` | `leagueid`, `league_name`, `league_tier` |
| result | `radiant_win` (BOOLEAN) | `radiant_win`; per draft row `team_won` |
| game mode | `game_mode` (2 = Captains Mode per `Constants.GameModes`) | filter only |
| hero | `picks_bans.hero_id` → `Constants.Heroes.id` / `localized_name` | `hero_id`, `hero_name` |
| pick or ban | `picks_bans.is_pick` | `is_pick` |
| side | `picks_bans.team`: **0 = Radiant, 1 = Dire**. Verified on 202609 `players.csv` (`isRadiant`): 700/700 picks agree. | `team`, `side` |
| draft order | `picks_bans.order` (0–23 in CM: 14 bans + 10 picks) | `draft_order` |

## Cleaning decisions

Raw: 75,000 match rows, all unique; 1,773,087 pick/ban rows covering 74,066 matches.

1. **Deduplicate.** No duplicate matches or exact duplicate draft rows were found. The code still dedups (`QUALIFY row_number()` on matches, `SELECT DISTINCT` on draft rows).
2. **Captains Mode only.** 73,605 matches. Dropped 869 All Pick, 426 Ranked AP, 51 mode 21, 46 Captains Draft and 3 Single Draft.
3. **Complete draft = exactly 5 picks per side.** That leaves 73,599 matches. Dropped:
   - 934 matches with no draft rows at all;
   - 182 with 1–9 or 11–14 picks;
   - 2 split 6/4 (only 6 of these were CM).
4. **Patch fix.** 646 clean matches (653 raw) are labelled patch 57 (7.38) but were played Aug–Sep 2024, before 7.38's release on 2025-02-19. Rule: if a match's labelled patch was released after the match started, reassign it to the latest patch released at or before the start time. Only these 646 matches change (57 → 56). The original value is kept in `matches.patch_id_original`.
5. Bans are **not** required to be complete. 356 of the kept matches have a ban count other than 14 (1,765,596 draft rows vs 73,599 × 24 = 1,766,376).

Final clean data: **73,599 matches, 1,765,596 draft rows**, 399 leagues, Radiant win rate 51.6%.

## Thresholds

| Name | Value | Where |
|---|---|---|
| Minimum matches per patch | 200 (`MIN_PATCH_MATCHES`) | `clean.py` → `patches.included` |
| Minimum picks for win-rate analysis | 100 per hero per patch | `sql/02_winrate_vs_pickrate.sql` |
| Overperformer | Wilson 95% CI lower bound > 50% | `sql/02` |
| Trap pick | pick rate ≥ the patch's 75th-percentile pick rate (among heroes with 100+ picks) **and** CI upper bound < 50% | `sql/02` |
| Low-sample month (chart only) | < 1,000 matches, drawn as hollow markers | `charts.py` |

## Patches

| id | patch | matches | note |
|---|---|---|---|
| 54 | 7.35 | 11,996 | truncated: the patch began 2023-12-14, data starts 2024-01-01 |
| 55 | 7.36 | 6,090 | |
| 56 | 7.37 | 15,978 | includes the 646 reassigned matches |
| 57 | 7.38 | 6,947 | |
| 58 | 7.39 | 17,389 | |
| 59 | 7.40 | 7,660 | |
| 60 | 7.41 | 7,539 | ongoing at the data cut-off (2026-09-13) |

**Dropped (< 200 matches): none.**

## Data caveats found

- Coverage drops sharply after May 2026. Clean matches per month were 907 (Jun), 420 (Jul), 659 (Aug) and 140 (Sep 1–13), compared with about 2,000–3,000 in earlier months. Monthly diversity for those months is biased low and is flagged in the chart.
- Draft folders hold yearly files up to 2025, so per-month analysis must use `start_time`, not folder names.

## Done (Day 1)

- [x] Selective extraction + DuckDB load (`load.py`), cleaning + Parquet (`clean.py`)
- [x] `sql/00_macros.sql` (Wilson CI macros), `01_meta_per_patch`, `02_winrate_vs_pickrate`, `03_patch_shifts`, `04_meta_diversity`
- [x] Result tables in `data/processed/` (DuckDB tables + Parquet with the same names)
- [x] Charts: `contest_heatmap`, `winrate_vs_pickrate`, `meta_diversity`, `risers_fallers` (shared style in `charts.py`, colours checked with the dataviz palette validator)
- [x] 5 pytest tests passing (Wilson CI, contest/pick/ban rates, entropy, patch shift, cleaned draft completeness)
- [x] Makefile (`data`, `analysis`, `figures`, `test`, `all`). `make` isn't installed on the dev machine; its commands were run directly.
- [x] WIP README with three findings

## Remaining for Day 2

- [ ] More analyses (one `.sql` each): first-pick/phase priorities using `draft_order`, Radiant vs Dire side win rate per patch, ban-vs-pick profiles (ban-heavy "respect bans"), hero pairs/synergy, league-tier differences (`league_tier`).
- [ ] Streamlit dashboard in `app/` (+ `make app` target, add `streamlit` to `requirements.txt`). It should read the Parquet files in `data/processed/`.
- [ ] Final README: full findings, dashboard screenshot, method notes (Wilson CI, effective number), limitations (coverage drop, truncated 7.35).
- [ ] Optional: diversity per patch (sample-size-robust), or bootstrap CIs for effective heroes.

## How to run

```bash
.venv/Scripts/python -m pip install -r requirements.txt
make all PY=.venv/Scripts/python ZIP=../archive.zip
# without make:
PYTHONPATH=src python -m dota_meta.load ../archive.zip && PYTHONPATH=src python -m dota_meta.clean
PYTHONPATH=src python -m dota_meta.metrics && PYTHONPATH=src python -m dota_meta.charts && python -m pytest -q
```
