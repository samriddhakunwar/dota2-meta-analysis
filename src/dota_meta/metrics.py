"""Run the analysis SQL files (sql/NN_name.sql) through DuckDB; each result becomes table <name> and a Parquet file."""
import sys
from pathlib import Path

import duckdb

from dota_meta.load import DB, ROOT

SQL = ROOT / "sql"
APP_DATA = ROOT / "data" / "app"  # small aggregated tables, committed so the dashboard deploys without the raw zip


def run(con: duckdb.DuckDBPyConnection, out_dir: Path | None = None) -> list[str]:
    """Execute macros then every analysis query in order. Returns the created table names."""
    tables = []
    for f in sorted(SQL.glob("*.sql")):
        name = f.stem.split("_", 1)[1]
        if name == "macros":
            con.execute(f.read_text(encoding="utf-8"))
            continue
        con.execute(f"CREATE OR REPLACE TABLE {name} AS {f.read_text(encoding='utf-8')}")
        if out_dir:
            con.execute(f"COPY {name} TO '{(out_dir / f'{name}.parquet').as_posix()}' (FORMAT parquet)")
        tables.append(name)
    return tables


def preview(con: duckdb.DuckDBPyConnection, table: str) -> str:
    """Top rows for the latest patch (per-hero tables) or the whole table (time series)."""
    cols = con.table(table).columns
    if table == "hero_synergy":
        return con.sql("""(SELECT * EXCLUDE (patch_id, hero_a, hero_b) FROM hero_synergy WHERE patch_id IS NULL
                           ORDER BY lift DESC LIMIT 8)
                          UNION ALL
                          (SELECT * EXCLUDE (patch_id, hero_a, hero_b) FROM hero_synergy WHERE patch_id IS NULL
                           ORDER BY lift LIMIT 8)""").df().to_string(index=False) + "\n\n" + con.sql("""
            -- noise check: if pair lifts were pure sampling noise, z = lift / SE would have variance ~1
            -- and ~2.5% of pairs would land in each tail at 95% confidence
            SELECT CASE WHEN patch_id IS NULL THEN 'pooled' ELSE 'per patch' END AS scope, count(*) AS pairs,
                   count(*) FILTER (label = 'synergy') / count(*) AS share_synergy,
                   count(*) FILTER (label = 'anti-synergy') / count(*) AS share_anti_synergy,
                   var_samp(lift / sqrt(expected_win_rate * (1 - expected_win_rate) / games)) AS var_z
            FROM hero_synergy GROUP BY 1 ORDER BY 1""").df().to_string(index=False)
    if "hero_id" not in cols:
        return con.sql(f"SELECT * FROM {table}").df().to_string(index=False)
    order = ("contest_rate_change DESC" if "contest_rate_change" in cols else "p1_contest_rate DESC"
             if "p1_contest_rate" in cols else "win_rate DESC" if "ci_low" in cols else "contest_rate DESC")
    return con.sql(f"""SELECT * EXCLUDE (hero_id, patch_id) FROM {table}
                       WHERE patch_id = (SELECT max(patch_id) FROM {table}) ORDER BY {order} LIMIT 12""").df().to_string(index=False)


if __name__ == "__main__":
    import pandas as pd

    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220, "display.max_columns", 20, "display.precision", 3)
    APP_DATA.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(DB) as con:
        tables = run(con, DB.parent)
        for t in tables:
            print(f"\n=== {t} ({con.sql(f'SELECT count(*) FROM {t}').fetchall()[0][0]:,} rows)")
            print(preview(con, t))
        for t in tables + ["patches"]:
            con.execute(f"COPY {t} TO '{(APP_DATA / f'{t}.parquet').as_posix()}' (FORMAT parquet)")
    size = sum(f.stat().st_size for f in APP_DATA.glob("*.parquet")) / 1e6
    print(f"\napp tables -> {APP_DATA.relative_to(ROOT).as_posix()}/ ({size:.2f} MB)")
