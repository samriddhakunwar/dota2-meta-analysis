-- Q4. Which heroes do teams grab or deny first?
-- Captains Mode order in this data (identical in every patch, draft_order 0-23):
--   phase 1 = slots 0-8   (7 bans, then 2 picks)
--   phase 2 = slots 9-17  (3 bans, then 6 picks)
--   phase 3 = slots 18-23 (4 bans, then 2 picks)
-- First-phase pick rate = first-phase picks / matches (2 per match, so rates sum to 200%); same for bans (sum to 700%).
-- p1_pick_share = share of the hero's picks that happen in phase 1 (how "first-pickable" it is when picked at all).
WITH hero_patch AS (
    SELECT patch_id, hero_id, hero_name,
           count(*) FILTER (is_pick AND draft_order <= 8)      AS p1_picks,
           count(*) FILTER (NOT is_pick AND draft_order <= 8)  AS p1_bans,
           count(*) FILTER (is_pick)                           AS picks
    FROM draft
    GROUP BY ALL
)
SELECT p.patch_id, p.patch_name, h.hero_id, h.hero_name,
       p.n_matches                              AS matches,
       h.p1_picks, h.p1_bans, h.picks,
       h.p1_picks / p.n_matches                 AS p1_pick_rate,
       h.p1_bans / p.n_matches                  AS p1_ban_rate,
       (h.p1_picks + h.p1_bans) / p.n_matches   AS p1_contest_rate,
       h.p1_picks / nullif(h.picks, 0)          AS p1_pick_share
FROM hero_patch h
JOIN patches p USING (patch_id)
WHERE p.included
ORDER BY p.patch_id, p1_contest_rate DESC
