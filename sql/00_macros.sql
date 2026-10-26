-- Wilson score interval for a binomial proportion (95%: z = 1.96).
CREATE OR REPLACE MACRO wilson_lower(k, n, z := 1.96) AS
    CASE WHEN n = 0 THEN NULL ELSE
    ((k / n) + z * z / (2 * n) - z * sqrt((k / n) * (1 - k / n) / n + z * z / (4 * n * n))) / (1 + z * z / n) END;
CREATE OR REPLACE MACRO wilson_upper(k, n, z := 1.96) AS
    CASE WHEN n = 0 THEN NULL ELSE
    ((k / n) + z * z / (2 * n) + z * sqrt((k / n) * (1 - k / n) / n + z * z / (4 * n * n))) / (1 + z * z / n) END;
