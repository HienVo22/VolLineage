"""Download season roster captures from the Wayback Machine (resumable, rate-limited).

    python -m scrapers.fetch_rosters                 # newest usable capture per season
    python -m scrapers.fetch_rosters --all-captures  # every unique capture (for capture comparison)
    python -m scrapers.fetch_rosters --seasons 2024 --force

Raw HTML is saved under data/raw/html/ and every attempt is logged to data/raw/manifest.jsonl,
so each parsed row can be traced back to the exact capture it came from.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone

from paths import HTML_DIR, MANIFEST, ROOT, SEASON_CAPTURES
from scrapers.sidearm import ExtractionError, extract_roster
from scrapers.wayback import Capture, WaybackClient


def html_path(year: int, timestamp: str):
    return HTML_DIR / f"roster_{year}_{timestamp}.html"


def load_manifest() -> dict[tuple[str, str], dict]:
    if not MANIFEST.exists():
        return {}
    entries = {}
    for line in MANIFEST.read_text().splitlines():
        if line.strip():
            entry = json.loads(line)
            entries[(str(entry["season_year"]), entry["timestamp"])] = entry
    return entries


def inspect(page: str, year: int) -> tuple[str, int, str | None]:
    try:
        roster = extract_roster(page)
    except ExtractionError as exc:
        return "no_roster_json", 0, str(exc)
    season = str((roster.get("season") or {}).get("title") or "")
    if season and season != str(year):
        return "season_mismatch", len(roster["players"]), f"page says season {season}"
    if not roster["players"]:
        return "empty_roster", 0, None
    return "ok", len(roster["players"]), None


def fetch_capture(client: WaybackClient, year: int, capture: Capture) -> dict:
    path = html_path(year, capture.timestamp)
    body = client.fetch(capture)
    path.write_bytes(body)
    page = body.decode("utf-8", errors="replace")
    status, players, note = inspect(page, year)
    return {
        "season_year": year,
        "timestamp": capture.timestamp,
        "original_url": capture.original,
        "raw_url": capture.raw_url,
        "cdx_digest": capture.digest,
        "sha1": hashlib.sha1(body).hexdigest(),
        "bytes": len(body),
        "file": str(path.relative_to(ROOT)),
        "parse_status": status,
        "players": players,
        "note": note,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seasons", type=int, nargs="*", help="only these seasons")
    parser.add_argument("--all-captures", action="store_true", help="fetch every unique capture")
    parser.add_argument("--force", action="store_true", help="re-download even if cached")
    args = parser.parse_args()

    if not SEASON_CAPTURES.exists():
        raise SystemExit("run `python -m scrapers.discover` first")
    seasons = json.loads(SEASON_CAPTURES.read_text())["seasons"]
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    client = WaybackClient()

    years = sorted(int(y) for y in seasons if not args.seasons or int(y) in args.seasons)
    with MANIFEST.open("a") as log:
        for year in years:
            captures = [Capture(**c) for c in seasons[str(year)]]
            # Newest first: later captures carry the most complete back-filled roster.
            for capture in sorted(captures, key=lambda c: c.timestamp, reverse=True):
                key = (str(year), capture.timestamp)
                cached = manifest.get(key)
                if cached and not args.force and html_path(year, capture.timestamp).exists():
                    entry = cached
                    origin = "cached"
                else:
                    try:
                        entry = fetch_capture(client, year, capture)
                    except RuntimeError as exc:
                        print(f"{year} {capture.timestamp}  FETCH FAILED  {exc}")
                        continue
                    manifest[key] = entry
                    log.write(json.dumps(entry) + "\n")
                    log.flush()
                    origin = "fetched"
                print(f"{year} {capture.timestamp}  {origin:<7}  {entry['parse_status']:<15} "
                      f"{entry['players']:>4} players  {entry['bytes'] / 1024:>6.0f} KB")
                if entry["parse_status"] == "ok" and not args.all_captures:
                    break

    usable = {k[0] for k, v in manifest.items() if v["parse_status"] == "ok"}
    missing = [y for y in years if str(y) not in usable]
    print(f"\n{len(manifest)} captures in manifest; {len(usable)} seasons usable; "
          f"{client.request_count} HTTP requests this run")
    if missing:
        print(f"seasons with no usable capture: {missing}")


if __name__ == "__main__":
    main()
