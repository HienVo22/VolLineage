"""Extractor for Sidearm-era season roster pages (utsports.com/sports/football/roster/YYYY).

These pages render the roster client-side with Vue. The full roster is embedded in
an inline script as `roster: {...}` JSON, which is more complete than the visible list.
"""

from __future__ import annotations

import html
import json
import re

MARKER = re.compile(r"\broster:\s*\{")

# Fields copied from the Sidearm player object into the shared record format.
PLAYER_FIELDS = [
    "first_name",
    "last_name",
    "jersey_number",
    "position_short",
    "position_long",
    "academic_year_short",
    "height_feet",
    "height_inches",
    "weight",
    "hometown",
    "highschool",
    "previous_school",
    "player_id",
    "rp_id",
]


class ExtractionError(ValueError):
    pass


def extract_roster(page: str) -> dict:
    """Return the embedded Sidearm roster object, or raise ExtractionError."""
    decoder = json.JSONDecoder()
    for match in MARKER.finditer(page):
        start = match.end() - 1
        try:
            obj, _ = decoder.raw_decode(page[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("players"), list):
            return obj
    raise ExtractionError("no embedded `roster: {...}` object with players")


def _clean(value):
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", html.unescape(value)).strip()
        return value or None
    return value


def roster_records(page: str, url_season: int, source_url: str, snapshot_timestamp: str) -> list[dict]:
    """One flat record per listed athlete, with capture provenance attached."""
    roster = extract_roster(page)
    page_season = (roster.get("season") or {}).get("title")
    records = []
    for player in roster["players"]:
        if player.get("rp_hide"):
            continue
        record = {field: _clean(player.get(field)) for field in PLAYER_FIELDS}
        record.update(
            season_year=url_season,
            page_season=_clean(page_season),
            roster_title=_clean(roster.get("title")),
            source_name="utsports_sidearm",
            source_url=source_url,
            snapshot_timestamp=snapshot_timestamp,
        )
        records.append(record)
    return records
