"""Hand-checkable tests: the real SQL files run on tiny in-memory tables, plus checks on the cleaned data."""
import math

import duckdb
import pytest

from dota_meta import metrics
from dota_meta.load import DB


def toy_db(draft_rows: list[tuple]) -> duckdb.DuckDBPyConnection:
    """draft_rows: (match_id, patch_id, month_day, is_pick, team, hero_id, team_won)."""
    con = duckdb.connect()
    con.execute("""CREATE TABLE draft (match_id INT, patch_id INT, patch_name VARCHAR, start_time TIMESTAMP,
                   draft_order INT, is_pick BOOL, team INT, side VARCHAR, hero_id INT, hero_name VARCHAR, team_won BOOL)""")
    for i, (m, p, day, pick, team, hero, won) in enumerate(draft_rows):
        con.execute("INSERT INTO draft VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [m, p, f"7.{p}", f"2025-{day}", i, pick, team, "radiant" if team == 0 else "dire", hero, f"H{hero}", won])
    con.execute("""CREATE TABLE patches AS
        SELECT patch_id, any_value(patch_name) patch_name, min(start_time) release_time,
               count(DISTINCT match_id) n_matches, true included FROM draft GROUP BY 1""")
    metrics.run(con)
    return con


def test_wilson_ci_known_values():
    con = duckdb.connect()
    con.execute((metrics.SQL / "00_macros.sql").read_text())
    lo, hi = con.sql("SELECT wilson_lower(5, 10), wilson_upper(5, 10)").fetchall()[0]
    # p = 0.5, n = 10: centre 0.5, half-width 1.96*sqrt(0.025 + 0.009604)/1.38416 = 0.26341
    assert lo == pytest.approx(0.23659, abs=1e-5) and hi == pytest.approx(0.76341, abs=1e-5)
    lo, hi = con.sql("SELECT wilson_lower(0, 10), wilson_upper(10, 10)").fetchall()[0]
    assert lo == pytest.approx(0, abs=1e-12) and hi == pytest.approx(1, abs=1e-12)  # stays inside [0, 1]
    assert con.sql("SELECT wilson_lower(0, 0)").fetchall()[0][0] is None


def test_contest_pick_ban_rates():
    # 2 matches. Hero 1: picked in m1 (won), banned in m2. Hero 2: picked in m2 (lost).
    con = toy_db([
        (1, 40, "01-05", True, 0, 1, True),
        (2, 40, "01-06", False, 1, 1, False),
        (2, 40, "01-06", True, 0, 2, False),
    ])
    r = {h: row for h, *row in con.sql(
        "SELECT hero_id, pick_rate, ban_rate, contest_rate, win_rate FROM meta_per_patch").fetchall()}
    assert r[1] == pytest.approx([0.5, 0.5, 1.0, 1.0])
    assert r[2][:3] == pytest.approx([0.5, 0.0, 0.5]) and r[2][3] == 0


def test_effective_number_of_heroes():
    # Jan: 4 heroes picked once each -> 4.  Feb: shares 0.5/0.25/0.25 -> exp(1.5 ln 2) = 2^1.5
    picks = [(1, 40, "01-05", True, 0, h, True) for h in (1, 2, 3, 4)]
    picks += [(2, 40, "02-05", True, 0, h, True) for h in (1, 1, 2, 3)]
    con = toy_db(picks)
    got = dict(con.sql("SELECT month::VARCHAR, effective_heroes FROM meta_diversity").fetchall())
    assert got["2025-01-01"] == pytest.approx(4)
    assert got["2025-02-01"] == pytest.approx(2 ** 1.5)
    assert dict(con.sql("SELECT month::VARCHAR, unique_heroes_picked FROM meta_diversity").fetchall())["2025-02-01"] == 3


def test_patch_shift_uses_previous_patch():
    con = toy_db([
        (1, 40, "01-05", True, 0, 1, True),           # patch 40: hero 1 contested 1/1
        (2, 41, "03-05", True, 0, 2, True),           # patch 41: 2 matches, hero 1 contested 1/2
        (3, 41, "03-06", False, 1, 1, False),
    ])
    (change,) = con.sql("SELECT contest_rate_change FROM patch_shifts WHERE hero_id = 1").fetchall()[0]
    assert change == pytest.approx(-0.5)
    assert not math.isnan(change)


@pytest.mark.skipif(not DB.exists(), reason="run `make data` first")
def test_cleaned_data_has_ten_picks_per_match():
    with duckdb.connect(DB, read_only=True) as con:
        bad = con.sql("""SELECT count(*) FROM (
            SELECT match_id FROM draft GROUP BY 1
            HAVING count(*) FILTER (is_pick) <> 10
                OR count(*) FILTER (is_pick AND team = 0) <> 5
                OR count(*) FILTER (is_pick AND team = 1) <> 5)""").fetchall()[0][0]
        n_matches, n_drafted, dupes = con.sql("""SELECT (SELECT count(*) FROM matches),
            (SELECT count(DISTINCT match_id) FROM draft),
            (SELECT count(*) - count(DISTINCT match_id) FROM matches)""").fetchall()[0]
    assert bad == 0
    assert n_matches == n_drafted and dupes == 0
