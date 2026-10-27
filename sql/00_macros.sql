-- Wilson score interval for a binomial proportion (95%: z = 1.96).
CREATE OR REPLACE MACRO wilson_lower(k, n, z := 1.96) AS
    CASE WHEN n = 0 THEN NULL ELSE
    ((k / n) + z * z / (2 * n) - z * sqrt((k / n) * (1 - k / n) / n + z * z / (4 * n * n))) / (1 + z * z / n) END;
CREATE OR REPLACE MACRO wilson_upper(k, n, z := 1.96) AS
    CASE WHEN n = 0 THEN NULL ELSE
    ((k / n) + z * z / (2 * n) + z * sqrt((k / n) * (1 - k / n) / n + z * z / (4 * n * n))) / (1 + z * z / n) END;
-- Expected win rate of two heroes on the same team if they don't interact:
-- add their individual win rates on the log-odds scale (each relative to a 50% baseline), then map back.
CREATE OR REPLACE MACRO logit(p) AS ln(p / (1 - p));
CREATE OR REPLACE MACRO expected_pair_win_rate(p_a, p_b) AS 1 / (1 + exp(-(logit(p_a) + logit(p_b))));
