"""Download Tennessee transfer-portal rows from CollegeFootballData.

    python -m scrapers.cfbd
    python -m scrapers.cfbd --years 2024
    python -m scrapers.cfbd --force

The portal endpoint returns every school for one season. This script keeps the raw
response, then writes only the rows where Tennessee is the origin or the destination.
It does not match those names to VolLineage players.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from paths import CFBD_DIR, PORTAL_CSV, PROCESSED

load_dotenv()

PORTAL_URL = "https://api.collegefootballdata.com/player/portal"
DEFAULT_YEARS = list(range(2021, 2026))
TENNESSEE_NAMES = {"tennessee", "tennessee volunteers"}


def is_tennessee(school: str | None) -> bool:
    return bool(school) and school.strip().lower() in TENNESSEE_NAMES


def raw_path(year: int) -> Path:
    return CFBD_DIR / f"portal_{year}.json"


def fetch_portal_year(session: requests.Session, year: int) -> list[dict]:
    response = session.get(PORTAL_URL, params={"year": year}, timeout=90)
    if response.status_code == 401:
        raise SystemExit(
            "CollegeFootballData returned 401. Add CFBD_API_KEY to .env "
            "(free key at https://collegefootballdata.com) and retry."
        )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise SystemExit(f"unexpected portal response for {year}: {type(payload).__name__}")
    return payload


def tennessee_rows(entries: list[dict]) -> list[dict]:
    """One flat row per Tennessee arrival or departure. Withdrawn entries stay in the file."""
    rows = []
    for entry in entries:
        origin = (entry.get("origin") or "").strip() or None
        destination = (entry.get("destination") or "").strip() or None
        arrived = is_tennessee(destination)
        left = is_tennessee(origin)
        if arrived == left:
            continue
        first = (entry.get("firstName") or "").strip()
        last = (entry.get("lastName") or "").strip()
        rows.append({
            "season_year": int(entry.get("season") or 0),
            "direction": "in" if arrived else "out",
            "player_name": f"{first} {last}".strip(),
            "other_school": origin if arrived else destination,
            "origin": origin,
            "destination": destination,
            "position": (entry.get("position") or "").strip() or None,
            "eligibility": (entry.get("eligibility") or "").strip() or None,
            "transfer_date": entry.get("transferDate"),
        })
    return rows


def cached_years() -> list[int]:
    years = []
    for path in CFBD_DIR.glob("portal_*.json"):
        year = path.stem.removeprefix("portal_")
        if year.isdigit():
            years.append(int(year))
    return sorted(years)


def load_raw_years(years: list[int]) -> list[dict]:
    entries = []
    for year in years:
        path = raw_path(year)
        if not path.exists():
            raise SystemExit(f"missing {path}. Run `python -m scrapers.cfbd --years {year}`.")
        entries.extend(json.loads(path.read_text()))
    return entries


def write_tennessee_csv(years: list[int]) -> pd.DataFrame:
    frame = pd.DataFrame(tennessee_rows(load_raw_years(years)))
    if frame.empty:
        raise SystemExit(f"no Tennessee portal rows in {years}")
    frame = frame.sort_values(["season_year", "direction", "player_name"]).reset_index(drop=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PORTAL_CSV, index=False)
    return frame


def print_counts(frame: pd.DataFrame) -> None:
    active = frame[frame.eligibility.fillna("") != "Withdrawn"]
    print(f"wrote {PORTAL_CSV} ({len(frame)} Tennessee rows, {len(active)} not withdrawn)")
    for year, group in frame.groupby("season_year"):
        kept = group[group.eligibility.fillna("") != "Withdrawn"]
        withdrawn = int((group.eligibility == "Withdrawn").sum())
        print(
            f"  {int(year)}  in {int((kept.direction == 'in').sum()):>3}  "
            f"out {int((kept.direction == 'out').sum()):>3}  withdrawn {withdrawn:>3}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", type=int, nargs="*", default=DEFAULT_YEARS)
    parser.add_argument("--force", action="store_true", help="re-download even if the JSON is cached")
    args = parser.parse_args()
    years = sorted(set(args.years))

    CFBD_DIR.mkdir(parents=True, exist_ok=True)
    key = os.getenv("CFBD_API_KEY", "").strip()
    session = requests.Session()
    session.headers["User-Agent"] = os.getenv(
        "VOLLINEAGE_USER_AGENT", "VolLineage COSC445 (University of Tennessee course project)"
    )
    if key:
        session.headers["Authorization"] = f"Bearer {key}"

    for year in years:
        path = raw_path(year)
        if path.exists() and not args.force:
            print(f"{year}: cached {path.name}")
            continue
        if not key:
            raise SystemExit(
                "CFBD_API_KEY is not set. Copy .env.example to .env, add a free key from "
                "https://collegefootballdata.com, and retry."
            )
        entries = fetch_portal_year(session, year)
        path.write_text(json.dumps(entries))
        print(f"{year}: downloaded {len(entries):,} portal rows -> {path.name}")

    # A one-year refresh must not drop the other cached seasons from the CSV.
    print_counts(write_tennessee_csv(cached_years()))


if __name__ == "__main__":
    main()
