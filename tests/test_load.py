import sqlite3

import pandas as pd

from pipeline.load import build


def row(sid, year, first, last, jersey, position, city="Murfreesboro", hs="Blackman", previous=None):
    return {
        "season_year": year, "sidearm_player_id": sid, "sidearm_rp_id": sid * 100 + year,
        "raw_name": f"{first} {last}", "first_name": first, "last_name": last, "suffix": None,
        "name_key": f"{first} {last}".lower(), "jersey_number": jersey, "position": position,
        "class_year": "SO", "redshirt": 0, "height_inches": 75, "weight_lbs": 200,
        "hometown_city": city, "home_state": "TN", "high_school": hs, "previous_school": previous,
        "source_name": "utsports_sidearm", "source_url": f"https://utsports.com/sports/football/roster/{year}",
        "snapshot_timestamp": "20241214044724", "qa_flag": None,
    }


def build_db(tmp_path, rows):
    db = tmp_path / "test.sqlite3"
    result = build(pd.DataFrame(rows), db_path=db)
    return result, sqlite3.connect(db)


def test_split_sidearm_ids_are_merged_when_hometown_and_school_agree(tmp_path):
    rows = [
        row(466, 2015, "Jauan", "Jennings", 15, "QB"),
        row(466, 2016, "Jauan", "Jennings", 15, "WR"),
        row(4192, 2018, "Jauan", "Jennings", 15, "WR"),
    ]
    result, con = build_db(tmp_path, rows)
    assert result["counts"]["players"] == 1
    aliases = {a for (a,) in con.execute("SELECT alias_text FROM player_aliases WHERE alias_type = 'source_id'")}
    assert aliases == {"sidearm:466", "sidearm:4192"}
    events = dict(con.execute("SELECT event_type, COUNT(*) FROM career_events GROUP BY event_type").fetchall())
    assert events["position_change"] == 1
    assert events["other"] == 1  # 2017 gap


def test_same_name_on_same_roster_stays_two_people(tmp_path):
    rows = [
        row(1, 2020, "Josh", "Smith", 10, "WR"),
        row(2, 2020, "Josh", "Smith", 30, "LB"),
    ]
    result, _ = build_db(tmp_path, rows)
    assert result["counts"]["players"] == 2
    assert result["decisions"] == {"distinct_same_season": 1}


def test_conflicting_hometown_goes_to_review_not_merge(tmp_path):
    rows = [
        row(1, 2019, "Cameron", "Miller", 40, "DB", city="Knoxville", hs="Bearden"),
        row(2, 2022, "Cameron", "Miller", 41, "DB", city="Memphis", hs="Memphis Acad."),
    ]
    result, con = build_db(tmp_path, rows)
    assert result["counts"]["players"] == 2
    note = con.execute("SELECT notes FROM player_aliases WHERE confidence < 1").fetchone()[0]
    assert "needs manual review" in note


def test_transfer_and_exit_events(tmp_path):
    rows = [
        row(1, 2023, "Joey", "Aguilar", 6, "QB", previous="UCLA"),
        row(1, 2024, "Joey", "Aguilar", 6, "QB"),
        row(2, 2023, "Other", "Player", 7, "WR"),
        row(2, 2024, "Other", "Player", 8, "WR"),
        row(3, 2023, "Gone", "Early", 9, "RB"),
    ]
    _, con = build_db(tmp_path, rows)
    q = "SELECT event_type, counterparty_school, from_value, to_value FROM career_events WHERE event_type != 'roster_join'"
    events = sorted(con.execute(q).fetchall())
    assert events == [("jersey_change", None, "7", "8"), ("roster_exit", None, None, None),
                      ("transfer_in", "UCLA", None, None)]
    status = con.execute("SELECT status FROM roster_entries WHERE raw_name = 'Joey Aguilar' ORDER BY season_year")
    assert [s for (s,) in status] == ["transfer_in", "active"]
