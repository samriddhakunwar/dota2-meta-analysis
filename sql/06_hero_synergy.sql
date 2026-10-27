-- Q5. Which same-team hero pairs win more (or less) than their individual strength predicts?
-- expected win rate = expected_pair_win_rate(hero A's win rate, hero B's win rate) in that patch (log-odds sum).
-- lift = observed pair win rate - expected (percentage points / 100). Wilson 95% CI on the observed rate.
--   synergy:      CI lower bound > expected
--   anti-synergy: CI upper bound < expected
-- Per patch, plus a pooled row per pair (patch_name 'All patches') whose expected wins add up the per-patch expectations.
-- Only pairs with at least 50 games together in the scope.
WITH pairs AS (
    SELECT a.patch_id, a.hero_id AS hero_a, b.hero_id AS hero_b, a.team_won
    FROM draft a
    JOIN draft b ON a.match_id = b.match_id AND a.team = b.team AND a.hero_id < b.hero_id
    WHERE a.is_pick AND b.is_pick
), scored AS (
    SELECT p.patch_id, p.hero_a, p.hero_b, p.team_won,
           expected_pair_win_rate(ma.win_rate, mb.win_rate) AS expected
    FROM pairs p
    JOIN meta_per_patch ma ON ma.patch_id = p.patch_id AND ma.hero_id = p.hero_a
    JOIN meta_per_patch mb ON mb.patch_id = p.patch_id AND mb.hero_id = p.hero_b
), agg AS (
    SELECT patch_id, hero_a, hero_b,
           count(*) AS games, count(*) FILTER (team_won) AS wins, sum(expected) AS expected_wins
    FROM scored
    GROUP BY GROUPING SETS ((patch_id, hero_a, hero_b), (hero_a, hero_b))
    HAVING count(*) >= 50
)
SELECT a.patch_id, coalesce(pt.patch_name, 'All patches') AS patch_name,
       a.hero_a, ha.hero_name AS hero_a_name, a.hero_b, hb.hero_name AS hero_b_name,
       a.games, a.wins,
       a.wins / a.games                         AS win_rate,
       a.expected_wins / a.games                AS expected_win_rate,
       a.wins / a.games - a.expected_wins / a.games AS lift,
       wilson_lower(a.wins, a.games)            AS ci_low,
       wilson_upper(a.wins, a.games)            AS ci_high,
       CASE WHEN wilson_lower(a.wins, a.games) > a.expected_wins / a.games THEN 'synergy'
            WHEN wilson_upper(a.wins, a.games) < a.expected_wins / a.games THEN 'anti-synergy'
            ELSE 'within noise' END             AS label
FROM agg a
LEFT JOIN patches pt USING (patch_id)
JOIN heroes ha ON ha.hero_id = a.hero_a
JOIN heroes hb ON hb.hero_id = a.hero_b
ORDER BY a.patch_id NULLS LAST, lift DESC
