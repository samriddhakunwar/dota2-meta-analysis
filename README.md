# Dota 2 Pro Meta & Draft Analysis

> **Status: in progress.** The data pipeline and the first three analyses are done. More analyses, a Streamlit dashboard and the final write-up are coming next.

Every Dota 2 patch reshuffles which of the 127 heroes professional teams fight over in the draft. This project takes **73,599 Captains Mode pro matches (Jan 2024 to Sep 2026, seven patches from 7.35 to 7.41)**, builds a reproducible SQL pipeline on DuckDB, and measures how the pro meta moves: which heroes define each patch, which popular picks actually lose, and whether the meta is getting narrower over time.

## Questions this project answers

1. **Meta per patch:** what are the pick, ban and contest rates of every hero in each patch?
2. **Win rate vs. pick rate:** which heroes win more than chance once you account for sample size, and which popular heroes are *trap picks*?
3. **Patch shifts and diversity:** which heroes rose and fell most between patches, and how many heroes does the pro scene effectively play?
4. *(coming next)* Draft-order and side effects, first-pick priorities, team/league breakdowns, interactive dashboard.

## Early findings

**1. Being contested doesn't mean winning.** In patch 7.41, Rubick is picked in **35.6%** of matches but wins **51.1%** of them (95% CI 49.2–52.9%), which is indistinguishable from a coin flip. **Shadow Fiend** is picked in **22.5%** of matches but wins only **47.5%** (CI 45.1–49.8%), so it's a *trap pick*. Meanwhile, niche heroes like **Lone Druid** (5.6% pick rate, 60.7% win rate, CI 56.0–65.2%) and **Keeper of the Light** (9.0%, 57.7%, CI 54.0–61.4%) clearly overperform. Every patch in the data has between 0 and 5 trap picks.

![Win rate vs pick rate](reports/figures/winrate_vs_pickrate.png)

**2. Patches flip the meta hard, and the top hero always falls.** In all six patch changes, the previous patch's most-contested hero became the **biggest faller** in the next patch: Timbersaw, Weaver, Phoenix, Tiny, Nature's Prophet and Jakiro. **Jakiro** went from the most-contested hero of 7.40 (**65.6%** of matches) to **16.0%** in 7.41, a fall of 49.6 percentage points, while **Pangolier** rose from **16.7%** to **57.0%**. Across the six patch changes, the top riser gained 27.0–44.4 points and the top faller lost 34.3–49.6 points.

![Risers and fallers](reports/figures/risers_fallers.png)
![Contest-rate heatmap](reports/figures/contest_heatmap.png)

**3. The pro meta is broad and stable.** In every month with at least 1,000 matches, pros picked **124–127 different heroes**. The *effective* number of heroes (exp of the Shannon entropy of picks) stays between **90.5 and 100.8** (mean 95.7 over 29 months), with no sign of the meta narrowing across patches. The drop after June 2026 is a small-sample effect: those months have under 1,000 matches in the dataset.

![Meta diversity](reports/figures/meta_diversity.png)

## Data

[Dota 2 Pro League Matches 2016–2026](https://www.kaggle.com/datasets/bwandowando/dota-2-pro-league-matches-2023) by **bwandowando** on Kaggle (OpenDota-sourced). The zip is 9.2 GB (48.5 GB uncompressed). The pipeline extracts only what it needs, about 85 MB: `main_metadata.csv` and `picks_bans.csv` from the 2024, 2025 and 2026-monthly folders, plus the `Constants/` lookup tables.

Cleaning (details in [PROGRESS.md](PROGRESS.md)):
- Captains Mode only.
- Exactly 10 picks per match (5 per side).
- Patch ids mapped to patch names.
- 646 matches labelled 7.38 but played before 7.38's release reassigned to 7.37 by date.
- Result: **73,599 of 75,000** matches kept.

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# download the Kaggle zip, then:
make all ZIP=path/to/archive.zip    # data -> analysis -> figures -> test
```

| Target | What it does |
|---|---|
| `make data` | selective unzip → DuckDB `data/processed/dota.duckdb` → clean tables + Parquet |
| `make analysis` | runs `sql/*.sql`, saves each result table to `data/processed/*.parquet` |
| `make figures` | renders the PNGs in `reports/figures/` (needs Chrome for kaleido) |
| `make test` | pytest |

## Repo structure

```
sql/                  one query per analysis question (+ Wilson CI macros)
src/dota_meta/
  load.py             selective extraction + raw CSV → DuckDB
  clean.py            dedupe, complete drafts, patch/hero mapping, Parquet export
  metrics.py          runs the SQL files through DuckDB
  charts.py           shared Plotly style + the README charts
tests/                hand-checkable tests (Wilson CI, contest rate, entropy, draft completeness)
reports/figures/      charts used in this README
app/                  Streamlit dashboard (coming next)
data/raw, data/processed   gitignored
```

## Tech stack

Python 3.12 · DuckDB (SQL) · pandas · Parquet (pyarrow) · Plotly + kaleido · pytest · Make
