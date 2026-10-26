"""Selectively extract the Kaggle zip and load raw CSVs into DuckDB."""
import re
import shutil
import sys
import zipfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "processed" / "dota.duckdb"
START_YEAR = 2024

# Folders are yearly (2016..2025) then monthly (202601..). Only these files are needed.
WANTED = re.compile(r"^(?P<folder>\d{4}|\d{6})/(main_metadata|picks_bans)\.csv$|^Constants/[^/]+\.csv$")


def extract(zip_path: Path, raw_dir: Path = RAW, start_year: int = START_YEAR) -> int:
    """Extract only match metadata, picks/bans (folders >= start_year) and Constants. Returns bytes written."""
    total = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            m = WANTED.match(info.filename)
            if not m or (m["folder"] and int(m["folder"][:4]) < start_year):
                continue
            out = raw_dir / info.filename
            out.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            total += info.file_size
    return total


def load_raw(con: duckdb.DuckDBPyConnection, raw_dir: Path = RAW) -> None:
    """Create raw_* tables straight from the CSVs (no cleaning)."""
    r = raw_dir.as_posix()
    con.sql(f"""CREATE OR REPLACE TABLE raw_matches AS
        SELECT * FROM read_csv('{r}/20*/main_metadata.csv', union_by_name=true)""")
    con.sql(f"""CREATE OR REPLACE TABLE raw_picks_bans AS
        SELECT * FROM read_csv('{r}/20*/picks_bans.csv', union_by_name=true)""")
    con.sql(f"CREATE OR REPLACE TABLE raw_heroes AS SELECT * FROM read_csv('{r}/Constants/Constants.Heroes.csv')")
    # patch names must stay text ("7.40" not 7.4); dates are UTC ISO strings
    con.sql(f"""CREATE OR REPLACE TABLE raw_patches AS
        SELECT * FROM read_csv('{r}/Constants/Constants.Patch.csv', types={{'patch': 'VARCHAR', 'date': 'VARCHAR'}})""")
    con.sql(f"CREATE OR REPLACE TABLE raw_leagues AS SELECT * FROM read_csv('{r}/Constants/Constants.Leagues.csv')")


def main(zip_path: str) -> None:
    for p in RAW.iterdir():  # rebuild from scratch, keep .gitkeep
        if p.name != ".gitkeep":
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    size = extract(Path(zip_path))
    print(f"extracted {size / 1e6:.1f} MB into {RAW}")
    DB.unlink(missing_ok=True)
    with duckdb.connect(DB) as con:
        load_raw(con)
        for t in ["raw_matches", "raw_picks_bans", "raw_heroes", "raw_patches", "raw_leagues"]:
            print(f"{t}: {con.sql(f'SELECT count(*) FROM {t}').fetchall()[0][0]:,} rows")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT.parent / "archive.zip"))
