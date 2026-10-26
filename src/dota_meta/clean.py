"""Build clean tables (matches, draft, heroes, patches) from raw_* tables and export Parquet."""
import duckdb

from dota_meta.load import DB

PROCESSED = DB.parent
CAPTAINS_MODE = 2
MIN_PATCH_MATCHES = 200


def clean(con: duckdb.DuckDBPyConnection) -> None:
    # patch id in match metadata = 0-based row position in Constants.Patch
    con.sql("""CREATE OR REPLACE TABLE patches AS
        SELECT (row_number() OVER () - 1)::INT AS patch_id, patch AS patch_name,
               replace(date, 'Z', '')::TIMESTAMP AS release_time
        FROM raw_patches""")
    unsorted = con.sql("""SELECT count(*) FROM (SELECT release_time < lag(release_time) OVER (ORDER BY patch_id) AS bad
                          FROM patches) WHERE bad""").fetchall()[0][0]
    assert unsorted == 0, "Constants.Patch is not in release order; positional patch ids would be wrong"

    con.sql("""CREATE OR REPLACE TABLE heroes AS
        SELECT id AS hero_id, localized_name AS hero_name, primary_attr, attack_type, roles FROM raw_heroes""")

    # one row per (match, draft slot); exact duplicates removed
    con.sql("CREATE OR REPLACE TEMP TABLE pb AS SELECT DISTINCT * FROM raw_picks_bans")
    con.sql("""CREATE OR REPLACE TEMP TABLE complete AS
        SELECT match_id FROM pb GROUP BY 1
        HAVING count(*) FILTER (is_pick AND team = 0) = 5 AND count(*) FILTER (is_pick AND team = 1) = 5""")

    funnel = con.sql(f"""SELECT
        (SELECT count(*) FROM raw_matches) AS raw_rows,
        (SELECT count(DISTINCT match_id) FROM raw_matches) AS unique_matches,
        (SELECT count(DISTINCT match_id) FROM raw_matches WHERE game_mode = {CAPTAINS_MODE}) AS captains_mode,
        (SELECT count(DISTINCT match_id) FROM raw_matches WHERE game_mode = {CAPTAINS_MODE}
            AND match_id IN (SELECT match_id FROM complete)) AS complete_draft""").df()
    print("cleaning funnel:\n" + funnel.to_string(index=False))

    # A few matches carry a patch id released *after* the match was played; reassign those by date.
    con.sql(f"""CREATE OR REPLACE TABLE matches AS
        WITH m AS (
            SELECT * FROM raw_matches
            WHERE game_mode = {CAPTAINS_MODE} AND match_id IN (SELECT match_id FROM complete)
            QUALIFY row_number() OVER (PARTITION BY match_id ORDER BY start_date_time) = 1
        ), fixed AS (
            SELECT m.*,
                   (SELECT max(patch_id) FROM patches p WHERE p.release_time <= m.start_date_time) AS patch_by_date
            FROM m
        )
        SELECT match_id, start_date_time AS start_time,
               start_date_time::DATE AS match_date,
               date_trunc('month', start_date_time)::DATE AS match_month,
               year(start_date_time) AS match_year,
               CASE WHEN lp.release_time > start_date_time THEN patch_by_date ELSE fixed.patch END AS patch_id,
               fixed.patch AS patch_id_original,
               leagueid, l.leaguename AS league_name, l.tier AS league_tier,
               radiant_win, duration, series_id, radiant_team_id, dire_team_id
        FROM fixed
        JOIN patches lp ON lp.patch_id = fixed.patch
        LEFT JOIN raw_leagues l USING (leagueid)""")
    con.sql("""CREATE OR REPLACE TABLE matches AS
        SELECT m.*, p.patch_name FROM matches m JOIN patches p USING (patch_id) ORDER BY start_time""")
    moved = con.sql("""SELECT patch_id_original, patch_id, count(*) n FROM matches
                       WHERE patch_id <> patch_id_original GROUP BY ALL ORDER BY ALL""").df()
    print("patch reassigned by date (original -> new):\n" + moved.to_string(index=False))

    con.sql("""CREATE OR REPLACE TABLE draft AS
        SELECT pb.match_id, m.patch_id, m.patch_name, m.start_time, pb."order" AS draft_order,
               pb.is_pick, pb.team, CASE pb.team WHEN 0 THEN 'radiant' ELSE 'dire' END AS side,
               pb.hero_id, h.hero_name,
               (pb.team = 0) = m.radiant_win AS team_won
        FROM pb JOIN matches m USING (match_id) JOIN heroes h USING (hero_id)
        ORDER BY pb.match_id, draft_order""")

    con.sql(f"""CREATE OR REPLACE TABLE patches AS
        SELECT p.*, coalesce(s.n_matches, 0) AS n_matches, s.first_match, s.last_match,
               coalesce(s.n_matches, 0) >= {MIN_PATCH_MATCHES} AS included
        FROM patches p LEFT JOIN (
            SELECT patch_id, count(*) n_matches, min(start_time) first_match, max(start_time) last_match
            FROM matches GROUP BY 1) s USING (patch_id)
        ORDER BY patch_id""")
    stats = con.sql("SELECT patch_id, patch_name, n_matches, first_match, last_match, included FROM patches WHERE n_matches > 0").df()
    print("matches per patch:\n" + stats.to_string(index=False))
    dropped = stats[~stats.included]
    print(f"patches dropped (< {MIN_PATCH_MATCHES} matches): " + (", ".join(dropped.patch_name) or "none"))

    for t in ["matches", "draft", "heroes", "patches"]:
        con.sql(f"COPY {t} TO '{(PROCESSED / f'{t}.parquet').as_posix()}' (FORMAT parquet)")
    print(f"clean tables: {con.sql('SELECT count(*) FROM matches').fetchall()[0][0]:,} matches, "
          f"{con.sql('SELECT count(*) FROM draft').fetchall()[0][0]:,} draft rows")


if __name__ == "__main__":
    with duckdb.connect(DB) as con:
        clean(con)
