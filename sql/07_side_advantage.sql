-- Q6. Does the Radiant side win more often, and does that change by patch?
-- Radiant win rate with a Wilson 95% CI, per included patch plus one pooled row (patch_name 'All patches').
SELECT patch_id, coalesce(patch_name, 'All patches') AS patch_name,
       count(*)                                   AS matches,
       count(*) FILTER (radiant_win)              AS radiant_wins,
       count(*) FILTER (radiant_win) / count(*)   AS radiant_win_rate,
       wilson_lower(count(*) FILTER (radiant_win), count(*)) AS ci_low,
       wilson_upper(count(*) FILTER (radiant_win), count(*)) AS ci_high
FROM matches
WHERE patch_id IN (SELECT patch_id FROM patches WHERE included)
GROUP BY GROUPING SETS ((patch_id, patch_name), ())
ORDER BY patch_id NULLS LAST
