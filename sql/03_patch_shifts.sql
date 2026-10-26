-- Q3a. Which heroes rose or fell the most between consecutive patches?
-- Change in contest rate (percentage points) from the previous included patch.
-- Heroes absent from either patch (e.g. newly released) are excluded.
WITH seq AS (
    SELECT patch_id, patch_name,
           lag(patch_id)   OVER (ORDER BY patch_id) AS prev_patch_id,
           lag(patch_name) OVER (ORDER BY patch_id) AS prev_patch_name
    FROM patches
    WHERE included
)
SELECT s.prev_patch_name || ' → ' || s.patch_name AS patch_change,
       s.patch_id, s.patch_name, s.prev_patch_name,
       cur.hero_id, cur.hero_name,
       prev.contest_rate                         AS prev_contest_rate,
       cur.contest_rate                          AS contest_rate,
       cur.contest_rate - prev.contest_rate      AS contest_rate_change,
       rank() OVER (PARTITION BY s.patch_id ORDER BY cur.contest_rate - prev.contest_rate DESC) AS riser_rank,
       rank() OVER (PARTITION BY s.patch_id ORDER BY cur.contest_rate - prev.contest_rate ASC)  AS faller_rank
FROM seq s
JOIN meta_per_patch cur  ON cur.patch_id = s.patch_id
JOIN meta_per_patch prev ON prev.patch_id = s.prev_patch_id AND prev.hero_id = cur.hero_id
ORDER BY s.patch_id, contest_rate_change DESC
