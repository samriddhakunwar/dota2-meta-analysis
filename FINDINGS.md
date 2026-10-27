# Findings: Dota 2 Pro Meta & Draft Analysis

All findings from Day 1 (2026-10-26) and Day 2 (2026-10-27). Every number comes from the pipeline output (`make analysis`) on **73,599 Captains Mode pro matches, Jan 2024 to Sep 2026, patches 7.35–7.41**. Methods and definitions are in the [README](README.md#methodology). Cleaning decisions and thresholds are in [PROGRESS.md](PROGRESS.md).

## Day 1: data

What the raw data actually looked like, and what cleaning found.

- **75,000** raw match rows, all unique, and **1,773,087** pick/ban rows covering 74,066 matches.
- **Captains Mode only:** 73,605 matches. Dropped 869 All Pick, 426 Ranked All Pick, 51 mode-21, 46 Captains Draft and 3 Single Draft matches.
- **Complete drafts (5 picks per side):** 73,599 matches kept. Of all raw matches, 934 had no draft rows at all, 182 had 1–9 or 11–14 picks, and 2 were split 6/4. Only 6 of these incomplete matches were Captains Mode.
- **Patch labelling error:** 646 clean matches were labelled 7.38 but played Aug–Sep 2024, before 7.38's release on 2025-02-19. They were reassigned to 7.37 by date.
- **Bans aren't always complete:** 356 kept matches have a ban count other than 14.
- **Side encoding verified:** `team` 0 = Radiant, 1 = Dire. All 700 of 700 picks in the 202609 `players.csv` agree.
- **Coverage drops after May 2026:** 907 clean matches in June, 420 in July, 659 in August and 140 in Sep 1–13, compared with about 2,000–3,000 a month earlier.
- **Patch sizes:** 7.35 has 11,996 matches (truncated: data starts 2024-01-01), 7.36 has 6,090, 7.37 has 15,978, 7.38 has 6,947, 7.39 has 17,389, 7.40 has 7,660, and 7.41 has 7,539 (ongoing at the cut-off).

## Day 1: meta, win rates and diversity

### 1. Being contested doesn't mean winning
Patch 7.41, heroes with at least 100 picks, Wilson 95% CIs:

| Hero | Pick rate | Win rate | 95% CI | Label |
|---|---|---|---|---|
| Rubick | 35.6% | 51.1% | 49.2–52.9% | within noise |
| Shadow Fiend | 22.5% | 47.5% | 45.1–49.8% | trap pick |
| Lone Druid | 5.6% | 60.7% | 56.0–65.2% | overperformer |
| Keeper of the Light | 9.0% | 57.7% | 54.0–61.4% | overperformer |

Trap picks per patch: 7.35: 3 · 7.36: 0 · 7.37: 5 · 7.38: 3 · 7.39: 5 · 7.40: 5 · 7.41: 2.

### 2. Patches flip the meta, and the top hero always falls
In all six patch changes, the previous patch's most-contested hero became the biggest faller in the next one:

| Change | Previous top hero = biggest faller |
|---|---|
| 7.35 → 7.36 | Timbersaw |
| 7.36 → 7.37 | Weaver |
| 7.37 → 7.38 | Phoenix |
| 7.38 → 7.39 | Tiny |
| 7.39 → 7.40 | Nature's Prophet |
| 7.40 → 7.41 | Jakiro |

- **Jakiro** fell from **65.6%** contest rate in 7.40 to **16.0%** in 7.41, a drop of 49.6 percentage points.
- **Pangolier** rose from **16.7%** to **57.0%** (+40.3 points).
- Across the six changes, the top riser gained 27.0–44.4 points and the top faller lost 34.3–49.6 points.

### 3. The pro meta is broad and stable
- In every month with at least 1,000 matches (29 months), pros picked **124–127 different heroes**.
- The effective number of heroes (exp of the Shannon entropy of picks) ranged from **90.5 to 100.8**, mean **95.7**.
- There's no sign of the meta narrowing across patches. The lower values after June 2026 are a small-sample effect.

## Day 2: draft, synergy and side

### 4. The first draft phase is about denial, and teams deny the heroes that win
Phase 1 = draft slots 0–8 (7 bans, then 2 picks). The slot layout is identical in all seven patches.

Patch 7.41, most first-phase-contested heroes:

| Hero | First-phase contest | Bans | Picks | Win rate (CI) |
|---|---|---|---|---|
| Lone Druid | 34.2% | 2,382 (31.6%) | 195 (2.6%) | 60.7% (56.0–65.2%), overperformer |
| Batrider | 31.2% | 27.6% | 3.5% | 55.7% (51.7–59.7%), overperformer |
| Beastmaster | 28.8% | 24.8% | 4.0% | 51.1% (47.9–54.2%), within noise |

Most first-phase-contested hero, and most first-phase-picked hero, in each patch:

| Patch | Top first-phase contest | Top first-phase pick |
|---|---|---|
| 7.35 | Timbersaw 44.4% | Vengeful Spirit 10.0% |
| 7.36 | Weaver 42.3% | Tiny 11.3% |
| 7.37 | Phoenix 31.5% | Rubick 8.0% |
| 7.38 | Tinker 41.8% | Jakiro 12.5% |
| 7.39 | Nature's Prophet 44.7% | Nature's Prophet 9.2% |
| 7.40 | **Jakiro 48.6%** (the highest of any patch) | Jakiro 13.8% |
| 7.41 | Lone Druid 34.2% | Rubick 12.3% |

In **5 of 6** patches with a successor (7.35, 7.36, 7.37, 7.39 and 7.40), the top first-phase target became the biggest contest-rate faller in the next patch (finding 2). The exception is 7.38: Tinker was the top first-phase target, but Tiny fell furthest. In other words, the heroes teams fear most early in the draft are usually the ones the next patch goes after.

### 5. Most hero-pair "synergy" is noise
Expected pair win rate = the two heroes' individual win rates added on the log-odds scale. Lift = observed − expected. Pairs need at least 50 games together.

- **6,507** pooled pairs: **137** synergy and **169** anti-synergy at 95% confidence, i.e. **4.7%** of pairs, about what chance alone would flag.
- Standardised lift variance is **0.967** pooled and **0.907** per patch (8,708 pairs). Pure sampling noise would give 1.0.
- The biggest lifts come from tiny samples. **Enchantress + Spectre** won 68.6% against an expected 47.9% (+20.8 points), but over only 51 games (CI 55.0–79.7%). **Kunkka + Lycan** won 28.3% against an expected 53.1% (−24.8 points), over 53 games.
- Among the 472 pairs with 500+ games, effects are small:

| Pair | Games | Observed | Expected | Lift | Label |
|---|---|---|---|---|---|
| Ursa + Disruptor | 584 | 52.7% | 47.2% | +5.6 pp | synergy |
| Axe + Ogre Magi | 813 | 52.6% | 47.3% | +5.4 pp | synergy |
| Luna + Jakiro | 557 | 53.7% | 49.0% | +4.7 pp | synergy |
| Jakiro + Gyrocopter | 548 | 43.4% | 48.4% | −4.9 pp | anti-synergy |
| Pangolier + Snapfire | 513 | 44.2% | 49.2% | −5.0 pp | anti-synergy |
| Shadow Fiend + Nature's Prophet | 510 | 48.0% | 54.2% | −6.2 pp | anti-synergy |

### 6. Radiant has a small but real edge

| Patch | Matches | Radiant win rate | 95% CI | Edge beyond chance? |
|---|---|---|---|---|
| 7.35 | 11,996 | 51.9% | 51.0–52.8% | yes |
| 7.36 | 6,090 | 50.6% | 49.4–51.9% | no |
| 7.37 | 15,978 | 50.4% | 49.6–51.1% | no |
| 7.38 | 6,947 | 52.5% | 51.3–53.7% | yes |
| 7.39 | 17,389 | 51.7% | 51.0–52.5% | yes |
| 7.40 | 7,660 | 52.3% | 51.2–53.5% | yes |
| 7.41 | 7,539 | 52.6% | 51.5–53.7% | yes |
| **All patches** | **73,599** | **51.6%** | **51.2–52.0%** | yes |

## Caveats
- The win rates are descriptive. Nothing here adjusts for team strength.
- With about 6,500 pairs tested, roughly 5% clear a 95% CI by chance, so a single flagged pair is a lead, not a result.
- Matches within a series aren't independent, so the CIs are slightly too narrow.
- In pro play, side choice is bundled with first-pick choice, so the Radiant edge may partly reflect draft order.
- 7.35 is truncated, 7.41 was ongoing at the cut-off, and coverage thins after May 2026.
