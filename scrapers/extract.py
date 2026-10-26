"""Parse every cached roster capture into one flat CSV of raw player rows.

    python -m scrapers.extract

Rows from all usable captures are kept. For each season, the capture listing the most
distinct athletes with a jersey or position (newest on ties) is marked
`selected_capture = 1`; the others stay available for capture-to-capture comparison.
"""

from __future__ import annotations

import json

import pandas as pd

from paths import MANIFEST, PROCESSED, ROOT, ROSTER_RAW
from scrapers.fetch_rosters import load_manifest
from scrapers.sidearm import roster_records


def athlete_count(records: list[dict]) -> int:
    """Distinct named athletes with a jersey or position; ignores repeated or placeholder rows."""
    return len({
        (r["first_name"], r["last_name"]) for r in records
        if r["jersey_number"] is not None or r["position_short"] is not None
    })


def main() -> None:
    if not MANIFEST.exists():
        raise SystemExit("run `python -m scrapers.fetch_rosters` first")
    manifest = load_manifest()

    parsed: dict[tuple[int, str], list[dict]] = {}
    for entry in sorted(manifest.values(), key=lambda e: (int(e["season_year"]), e["timestamp"])):
        if entry["parse_status"] != "ok":
            continue
        year = int(entry["season_year"])
        page = (ROOT / entry["file"]).read_bytes().decode("utf-8", errors="replace")
        parsed[(year, entry["timestamp"])] = roster_records(page, year, entry["original_url"], entry["timestamp"])

    selected: dict[int, str] = {}
    for (year, ts), records in sorted(parsed.items(), key=lambda kv: (athlete_count(kv[1]), kv[0][1])):
        selected[year] = ts  # sorted ascending, so the best capture per season is written last

    rows = []
    for (year, ts), records in parsed.items():
        for record in records:
            record["selected_capture"] = int(selected[year] == ts)
            rows.append(record)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows).sort_values(["season_year", "snapshot_timestamp"], kind="stable")
    df.to_csv(ROSTER_RAW, index=False)

    chosen = df[df.selected_capture == 1]
    skipped = sum(1 for e in manifest.values() if e["parse_status"] != "ok")
    print(f"parsed {len(parsed)} captures -> {len(df):,} raw rows "
          f"({skipped} captures had no usable roster)")
    print(f"selected one capture per season: {chosen.season_year.nunique()} seasons, {len(chosen):,} rows")
    print(f"wrote {ROSTER_RAW}")
    print(json.dumps({int(k): int(v) for k, v in chosen.groupby("season_year").size().items()}))


if __name__ == "__main__":
    main()
