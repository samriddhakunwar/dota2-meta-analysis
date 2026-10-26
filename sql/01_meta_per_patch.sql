-- Q1. What is the meta in each patch?
-- Pick rate, ban rate and contest rate ((picks + bans) / matches) per hero per patch.
-- Only heroes picked or banned at least once in the patch appear; only patches with enough matches (patches.included).
WITH hero_patch AS (
    SELECT patch_id, hero_id, hero_name,
           count(*) FILTER (is_pick)               AS picks,
           count(*) FILTER (NOT is_pick)           AS bans,
           count(*) FILTER (is_pick AND team_won)  AS wins
    FROM draft
    GROUP BY ALL
)
SELECT p.patch_id, p.patch_name, h.hero_id, h.hero_name,
       p.n_matches                              AS matches,
       h.picks, h.bans, h.wins,
       h.picks / p.n_matches                    AS pick_rate,
       h.bans / p.n_matches                     AS ban_rate,
       (h.picks + h.bans) / p.n_matches         AS contest_rate,
       h.wins / nullif(h.picks, 0)              AS win_rate
FROM hero_patch h
JOIN patches p USING (patch_id)
WHERE p.included
ORDER BY p.patch_id, contest_rate DESC
