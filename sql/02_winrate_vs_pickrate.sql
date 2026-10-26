-- Q2. Which heroes win more (or less) than their popularity suggests?
-- Win rate with a Wilson 95% CI, for heroes with at least 100 picks in the patch.
--   overperformer: CI lower bound > 50%
--   trap pick:     pick rate in the patch's top quartile (among qualifying heroes) and CI upper bound < 50%
WITH qualified AS (
    SELECT *,
           wilson_lower(wins, picks) AS ci_low,
           wilson_upper(wins, picks) AS ci_high,
           quantile_cont(pick_rate, 0.75) OVER (PARTITION BY patch_id) AS pick_rate_p75
    FROM meta_per_patch
    WHERE picks >= 100
)
SELECT patch_id, patch_name, hero_id, hero_name, matches, picks, wins,
       pick_rate, win_rate, ci_low, ci_high, pick_rate_p75,
       CASE WHEN ci_low > 0.5 THEN 'overperformer'
            WHEN pick_rate >= pick_rate_p75 AND ci_high < 0.5 THEN 'trap pick'
            ELSE 'within noise' END AS label
FROM qualified
ORDER BY patch_id, win_rate DESC
