"""Enumerate Wayback captures of the per-season UTSports roster pages.

    python -m scrapers.discover                     # 1998-2025 season pages
    python -m scrapers.discover --start 2020 --end 2025
    python -m scrapers.discover --inventory         # capture counts for every site era (slow)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone

from paths import CDX_DIR, ERA_INVENTORY, SEASON_CAPTURES
from scrapers.wayback import WaybackClient

SEASON_URL = "utsports.com/sports/football/roster/{year}"

# URL pattern (and optional regex on the original URL) for each platform the athletics site has used.
# roster.aspx is shared by every sport, so it needs the path=football filter.
ERAS = [
    ("CollegeSports/CSTV", "utsports.collegesports.com/sports/m-footbl/*", None),
    ("CBS m-footbl", "utsports.com/sports/m-footbl/*", None),
    ("Sidearm roster.aspx (football)", "utsports.com/roster.aspx*", "original:.*path=football.*"),
    ("Sidearm /sports/football/roster", "utsports.com/sports/football/roster*", None),
]


def discover_seasons(client: WaybackClient, start: int, end: int) -> dict:
    existing = json.loads(SEASON_CAPTURES.read_text()) if SEASON_CAPTURES.exists() else {}
    seasons = existing.get("seasons", {})
    for year in range(start, end + 1):
        captures = client.cdx(SEASON_URL.format(year=year))
        seasons[str(year)] = [asdict(c) for c in captures]
        span = f"{captures[0].timestamp[:8]}..{captures[-1].timestamp[:8]}" if captures else "-"
        print(f"{year}: {len(captures):>2} unique captures  {span}")
    return {
        "queried_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "url_template": SEASON_URL,
        "seasons": dict(sorted(seasons.items())),
    }


def inventory(client: WaybackClient) -> dict:
    counts = {}
    for label, pattern, url_filter in ERAS:
        extra = {"filter": ["statuscode:200", url_filter]} if url_filter else {}
        n = client.count_unique(pattern, **extra)
        counts[label] = {"pattern": pattern, "unique_captures": n}
        print(f"{label:<34} {pattern:<48} {n:>7,}")
    print(f"{'Total':<83} {sum(v['unique_captures'] for v in counts.values()):>7,}")
    return {"queried_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "eras": counts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=int, default=1998)
    parser.add_argument("--end", type=int, default=2025)
    parser.add_argument("--inventory", action="store_true", help="count captures per site era instead")
    args = parser.parse_args()

    CDX_DIR.mkdir(parents=True, exist_ok=True)
    client = WaybackClient(min_interval=1.0)
    if args.inventory:
        ERA_INVENTORY.write_text(json.dumps(inventory(client), indent=2))
        print(f"wrote {ERA_INVENTORY}")
        return
    result = discover_seasons(client, args.start, args.end)
    SEASON_CAPTURES.write_text(json.dumps(result, indent=2))
    total = sum(len(v) for v in result["seasons"].values())
    print(f"wrote {SEASON_CAPTURES} ({len(result['seasons'])} seasons, {total} captures, "
          f"{client.request_count} CDX requests)")


if __name__ == "__main__":
    main()
