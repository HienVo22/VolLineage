"""Normalize the selected capture for each season into analysis-ready rows.

    python -m pipeline.clean

Raw values are kept next to their cleaned versions so every transformation is auditable.
"""

from __future__ import annotations

import pandas as pd

from paths import ROSTER_CLEAN, ROSTER_RAW
from pipeline import normalize as n


def clean_row(series: pd.Series) -> dict:
    row = {k: (None if pd.isna(v) else v) for k, v in series.items()}
    first, last = row.get("first_name"), row.get("last_name")
    last_no_suffix, suffix = n.split_suffix(last)
    class_year, redshirt = n.parse_class(row.get("academic_year_short"))
    city, state = n.parse_hometown(row.get("hometown"))
    previous = row.get("previous_school")
    return {
        "season_year": int(row["season_year"]),
        "sidearm_player_id": int(row["player_id"]) if row.get("player_id") is not None else None,
        "sidearm_rp_id": int(row["rp_id"]) if row.get("rp_id") is not None else None,
        "raw_name": n.display_name(first, last),
        "first_name": first,
        "last_name": last_no_suffix,
        "suffix": suffix,
        "name_key": n.name_key(first, last),
        "jersey_raw": row.get("jersey_number"),
        "jersey_number": n.parse_jersey(row.get("jersey_number")),
        "position_raw": row.get("position_short"),
        "position": n.clean_position(row.get("position_short")),
        "class_raw": row.get("academic_year_short"),
        "class_year": class_year,
        "redshirt": redshirt,
        "height_inches": n.height_inches(row.get("height_feet"), row.get("height_inches")),
        "weight_lbs": n.parse_weight(row.get("weight")),
        "hometown_raw": row.get("hometown"),
        "hometown_city": city,
        "home_state": state,
        "high_school": row.get("highschool"),
        "previous_school": previous.strip() if isinstance(previous, str) and previous.strip() else None,
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "snapshot_timestamp": str(row["snapshot_timestamp"]),
    }


def qa_flags(clean: pd.DataFrame) -> pd.Series:
    """Mark rows the loader should skip. Input must be sorted so the first listing comes first."""
    flags = pd.Series([None] * len(clean), index=clean.index, dtype=object)
    flags[clean.jersey_raw.isna() & clean.position_raw.isna()] = "no_jersey_no_position"
    repeat = clean.duplicated(["sidearm_player_id", "season_year"], keep="first")
    flags[repeat & flags.isna()] = "repeat_listing_same_season"
    return flags


def main() -> None:
    if not ROSTER_RAW.exists():
        raise SystemExit("run `python -m scrapers.extract` first")
    raw = pd.read_csv(ROSTER_RAW, dtype={"jersey_number": str, "snapshot_timestamp": str})
    selected = raw[raw.selected_capture == 1]
    clean = pd.DataFrame([clean_row(r) for _, r in selected.iterrows()])
    clean = clean.sort_values(["season_year", "last_name", "first_name", "sidearm_rp_id"]).reset_index(drop=True)
    clean["qa_flag"] = qa_flags(clean)
    clean.to_csv(ROSTER_CLEAN, index=False)

    with_state = clean.hometown_raw.dropna()
    with_state = with_state[with_state.str.contains(",")]
    print(f"cleaned {len(clean):,} rows across {clean.season_year.nunique()} seasons -> {ROSTER_CLEAN}")
    print(f"  class labels   {clean.class_raw.nunique():>3} raw variants -> {clean.class_year.nunique()} codes "
          f"(+ redshirt flag on {int(clean.redshirt.sum())} rows)")
    print(f"  hometown state {with_state.str.rpartition(',')[2].str.strip().nunique():>3} raw variants "
          f"-> {clean.home_state.nunique()} values; {int(clean.home_state.isna().sum())} rows list a bare city")
    print(f"  positions      {clean.position_raw.nunique():>3} raw variants -> {clean.position.nunique()} codes")
    print(f"  QA flags (rows kept in CSV, skipped by loader): {clean.qa_flag.value_counts().to_dict()}")
    unparsed = {
        "jersey": int((clean.jersey_raw.notna() & clean.jersey_number.isna()).sum()),
        "class": int((clean.class_raw.notna() & clean.class_year.isna()).sum()),
        "height": int(clean.height_inches.isna().sum()),
        "weight": int(clean.weight_lbs.isna().sum()),
    }
    print(f"  null or unparseable after cleaning: {unparsed}")


if __name__ == "__main__":
    main()
