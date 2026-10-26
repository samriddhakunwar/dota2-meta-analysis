"""Run the analysis SQL files (sql/NN_name.sql) through DuckDB; each result becomes table <name> and a Parquet file."""
import sys
from pathlib import Path

import duckdb

from dota_meta.load import DB, ROOT

SQL = ROOT / "sql"


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
    if "hero_id" not in cols:
        return con.sql(f"SELECT * FROM {table}").df().to_string(index=False)
    order = "contest_rate_change DESC" if "contest_rate_change" in cols else (
        "win_rate DESC" if "ci_low" in cols else "contest_rate DESC")
    return con.sql(f"""SELECT * EXCLUDE (hero_id, patch_id) FROM {table}
                       WHERE patch_id = (SELECT max(patch_id) FROM {table}) ORDER BY {order} LIMIT 12""").df().to_string(index=False)


if __name__ == "__main__":
    import pandas as pd

    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220, "display.max_columns", 20, "display.precision", 3)
    with duckdb.connect(DB) as con:
        for t in run(con, DB.parent):
            print(f"\n=== {t} ({con.sql(f'SELECT count(*) FROM {t}').fetchall()[0][0]:,} rows)")
            print(preview(con, t))
