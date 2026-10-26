-- Q3b. Is the meta getting more or less diverse over time?
-- Per month: unique heroes picked, and the effective number of heroes = exp(Shannon entropy of the pick distribution).
-- Effective number = N if all N heroes are picked equally; lower when picks concentrate on a few heroes.
WITH picks AS (
    SELECT date_trunc('month', start_time)::DATE AS month, hero_id, count(*) AS n
    FROM draft
    WHERE is_pick
    GROUP BY ALL
), shares AS (
    SELECT month, hero_id, n, n / sum(n) OVER (PARTITION BY month) AS p
    FROM picks
), months AS (
    SELECT date_trunc('month', start_time)::DATE AS month,
           count(DISTINCT match_id) AS matches,
           mode(patch_name) AS main_patch
    FROM draft
    GROUP BY 1
)
SELECT s.month, m.main_patch, m.matches,
       count(*)                       AS unique_heroes_picked,
       exp(-sum(s.p * ln(s.p)))       AS effective_heroes
FROM shares s JOIN months m USING (month)
GROUP BY ALL
ORDER BY s.month
