"""Show one athlete's resolved history with provenance.

    python -m analysis.lineage "Jauan Jennings"
    python -m analysis.lineage Hardesty
"""

from __future__ import annotations

import sqlite3
import sys

import pandas as pd

from paths import DB

ROSTER_SQL = """
SELECT r.season_year AS season, r.raw_name AS listed_as, r.jersey_number AS jersey, r.position AS pos,
       r.class_year || CASE WHEN r.redshirt THEN ' (RS)' ELSE '' END AS class,
       r.height_inches AS ht, r.weight_lbs AS wt, r.status,
       r.snapshot_timestamp AS wayback_capture
FROM roster_entries r WHERE r.player_id = ? ORDER BY r.season_year
"""
ALIAS_SQL = """
SELECT alias_type, alias_text, season_year, confidence, notes
FROM player_aliases WHERE player_id = ? AND alias_type != 'jersey' ORDER BY alias_type, alias_text
"""
EVENT_SQL = """
SELECT season_year AS season, event_type, from_value, to_value, counterparty_school, notes
FROM career_events WHERE player_id = ? ORDER BY season_year, event_id
"""


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    query = " ".join(sys.argv[1:])
    con = sqlite3.connect(DB)
    matches = con.execute(
        "SELECT player_id, canonical_name, hometown, home_state, high_school, notes FROM players "
        "WHERE canonical_name LIKE ? ORDER BY canonical_name LIMIT 5", (f"%{query}%",),
    ).fetchall()
    if not matches:
        raise SystemExit(f"no player matching {query!r}")
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 70)
    for pid, name, city, state, hs, notes in matches:
        print(f"\n### {name}  (VolLineage player_id {pid}; {city or '?'}, {state or '?'}; HS: {hs or '?'}; {notes})")
        print(pd.read_sql(ROSTER_SQL, con, params=(pid,)).to_string(index=False))
        print("\naliases / identity evidence:")
        print(pd.read_sql(ALIAS_SQL, con, params=(pid,)).to_string(index=False))
        print("\ncareer events:")
        print(pd.read_sql(EVENT_SQL, con, params=(pid,)).to_string(index=False))


if __name__ == "__main__":
    main()
