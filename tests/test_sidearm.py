from pathlib import Path

import pytest

from scrapers.fetch_rosters import inspect
from scrapers.sidearm import ExtractionError, extract_roster, roster_records

FIXTURE = (Path(__file__).parent / "fixtures" / "sidearm_roster_2013.html").read_text()
URL = "https://utsports.com/sports/football/roster/2013"


def test_extracts_embedded_roster_json():
    roster = extract_roster(FIXTURE)
    assert roster["season"]["title"] == "2013"
    assert len(roster["players"]) == 4


def test_records_skip_hidden_players_and_keep_provenance():
    records = roster_records(FIXTURE, 2013, URL, "20220419182347")
    assert [r["last_name"] for r in records] == ["Arnold", "Ashford", "Johnson Jr."]
    assert all(r["source_url"] == URL and r["snapshot_timestamp"] == "20220419182347" for r in records)
    assert all(r["season_year"] == 2013 and r["page_season"] == "2013" for r in records)


def test_records_collapse_whitespace_and_blank_strings():
    ashford = roster_records(FIXTURE, 2013, URL, "x")[1]
    assert ashford["highschool"] == "Morristown West"
    assert ashford["position_short"] == "QB"
    arnold = roster_records(FIXTURE, 2013, URL, "x")[0]
    assert arnold["previous_school"] is None


def test_page_without_roster_json_is_rejected():
    with pytest.raises(ExtractionError):
        extract_roster("<html><script>window.__NUXT__ = {}</script></html>")
    assert inspect("<html></html>", 2013)[0] == "no_roster_json"


def test_season_mismatch_is_flagged():
    status, players, note = inspect(FIXTURE, 2014)
    assert status == "season_mismatch"
    assert "2013" in note
