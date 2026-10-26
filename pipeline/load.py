"""Build db/vollineage.sqlite3 from the cleaned roster rows.

    python -m pipeline.load

Resolution prototype (rules are deliberately simple and explainable):
  1. Start from Sidearm's own `player_id`. It is NOT stable: back-filled seasons (pre-2008 and some
     later years) were given new ids, so one athlete can carry two or three ids.
  2. Block on last name, then compare every pair of Sidearm ids:
       - listed on the same season roster          -> different people, never merged
       - career span would exceed 6 seasons         -> different people
       - identical name + same hometown or high school, no contradicting field -> auto-merge (0.95)
       - otherwise similar name                     -> review queue with a score, not merged
  3. Career events (join, exit, jersey change, position change, transfer in) are derived per player.
"""

from __future__ import annotations

import sqlite3
from difflib import SequenceMatcher
from itertools import combinations

import pandas as pd

from paths import DB, REVIEW_QUEUE, ROSTER_CLEAN, SCHEMA

SOURCE = "utsports_sidearm"
MAX_CAREER_SEASONS = 6
AUTO_MERGE_CONFIDENCE = 0.95

HEAD_COACHES = [
    (1998, 2008, "Phillip Fulmer"),
    (2009, 2009, "Lane Kiffin"),
    (2010, 2012, "Derek Dooley"),
    (2013, 2017, "Butch Jones"),
    (2018, 2020, "Jeremy Pruitt"),
    (2021, 2100, "Josh Heupel"),
]


def head_coach(year: int) -> str:
    return next(name for start, end, name in HEAD_COACHES if start <= year <= end)


def nn(value):
    """pandas NaN/NA -> None so sqlite stores NULL; numpy scalars -> Python."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    return value.item() if hasattr(value, "item") else value


def latest(series: pd.Series):
    values = series.dropna()
    return nn(values.iloc[-1]) if len(values) else None


def text_match(a, b, threshold: float = 1.0) -> bool | None:
    """True/False when both values exist, None when either is missing."""
    a, b = nn(a), nn(b)
    if not a or not b:
        return None
    a, b = a.strip().lower(), b.strip().lower()
    return a == b or SequenceMatcher(None, a, b).ratio() >= threshold


def compare(a: dict, b: dict) -> dict:
    first_sim = SequenceMatcher(None, a["first_key"], b["first_key"]).ratio()
    overlap = sorted(set(a["seasons"]) & set(b["seasons"]))
    span = max(a["seasons"] + b["seasons"]) - min(a["seasons"] + b["seasons"]) + 1
    same_city = text_match(a["city"], b["city"])
    same_hs = text_match(a["high_school"], b["high_school"], threshold=0.85)
    exact = a["name_key"] == b["name_key"]

    if overlap:
        decision = "distinct_same_season"
    elif span > MAX_CAREER_SEASONS:
        decision = "distinct_career_too_long"
    elif exact and (same_city or same_hs) and same_city is not False and same_hs is not False:
        decision = "auto_merge"
    elif exact and (same_city or same_hs):
        decision = "review_conflicting_fields"
    else:
        decision = "review"
    score = 0.5 * first_sim + 0.25 * bool(same_city) + 0.25 * bool(same_hs)
    return {
        "sidearm_id_a": a["sidearm_player_id"], "name_a": a["name"], "seasons_a": a["seasons"],
        "hometown_a": a["city"], "high_school_a": a["high_school"],
        "sidearm_id_b": b["sidearm_player_id"], "name_b": b["name"], "seasons_b": b["seasons"],
        "hometown_b": b["city"], "high_school_b": b["high_school"],
        "first_name_similarity": round(first_sim, 2), "same_hometown": same_city,
        "same_high_school": same_hs, "career_span": span, "score": round(score, 2), "decision": decision,
    }


def candidate_pairs(df: pd.DataFrame) -> pd.DataFrame:
    people = []
    for sid, rows in df.sort_values("season_year").groupby("sidearm_player_id"):
        key = rows.name_key.iloc[-1]
        people.append({
            "sidearm_player_id": int(sid), "name": rows.raw_name.iloc[-1], "name_key": key,
            "first_key": key.split(" ", 1)[0], "last_key": key.split(" ", 1)[-1],
            "city": latest(rows.hometown_city), "high_school": latest(rows.high_school),
            "seasons": sorted(int(s) for s in rows.season_year.unique()),
        })
    out = []
    for _, block in pd.DataFrame(people).groupby("last_key"):
        for a, b in combinations(block.to_dict("records"), 2):
            similar = SequenceMatcher(None, a["first_key"], b["first_key"]).ratio() >= 0.75
            prefix = a["first_key"].startswith(b["first_key"]) or b["first_key"].startswith(a["first_key"])
            if similar or prefix:
                out.append(compare(a, b))
    return pd.DataFrame(out)


def resolve(df: pd.DataFrame, pairs: pd.DataFrame) -> tuple[dict[int, int], dict[int, float]]:
    """Union-find over auto-merge pairs. Returns sidearm id -> VolLineage player id, and merge confidence."""
    parent = {int(s): int(s) for s in df.sidearm_player_id.unique()}
    seasons = {int(s): set(g.season_year) for s, g in df.groupby("sidearm_player_id")}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    confidence: dict[int, float] = {}
    merges = pairs[pairs.decision == "auto_merge"] if len(pairs) else pairs
    for r in merges.to_dict("records"):
        ra, rb = find(r["sidearm_id_a"]), find(r["sidearm_id_b"])
        if ra == rb or seasons[ra] & seasons[rb]:
            continue  # never put one person on the same season roster twice
        root, child = min(ra, rb), max(ra, rb)
        parent[child] = root
        seasons[root] |= seasons.pop(child)
        confidence[r["sidearm_id_a"]] = confidence[r["sidearm_id_b"]] = AUTO_MERGE_CONFIDENCE

    # Stable VolLineage ids: ordered by first season, then name.
    roots = (
        df.assign(root=df.sidearm_player_id.map(lambda s: find(int(s))))
        .groupby("root").agg(first=("season_year", "min"), name=("name_key", "first"))
        .sort_values(["first", "name"]).index
    )
    vl_id = {root: i for i, root in enumerate(roots, start=1)}
    return {sid: vl_id[find(sid)] for sid in parent}, confidence


def career_events(records: list[dict], last_season: int) -> list[tuple]:
    """`records` must use None (not NaN) for missing values."""
    by_player: dict[int, list[dict]] = {}
    for row in sorted(records, key=lambda r: r["season_year"]):
        by_player.setdefault(row["player_id"], []).append(row)
    events = []
    for pid, rows in by_player.items():
        first, final = rows[0], rows[-1]
        events.append((pid, first["season_year"], "roster_join", None, None, None, None, first["source_url"]))
        if first["previous_school"]:
            events.append((pid, first["season_year"], "transfer_in", None, None, first["previous_school"],
                           "previous_school listed at first appearance", first["source_url"]))
        for prev, cur in zip(rows, rows[1:]):
            url = cur["source_url"]
            if cur["season_year"] - prev["season_year"] > 1:
                events.append((pid, cur["season_year"], "other", str(prev["season_year"]),
                               str(cur["season_year"]), None, "gap in roster appearances", url))
            if prev["jersey_number"] is not None and cur["jersey_number"] is not None \
                    and prev["jersey_number"] != cur["jersey_number"]:
                events.append((pid, cur["season_year"], "jersey_change", str(prev["jersey_number"]),
                               str(cur["jersey_number"]), None, None, url))
            if prev["position"] and cur["position"] and prev["position"] != cur["position"]:
                events.append((pid, cur["season_year"], "position_change", prev["position"],
                               cur["position"], None, None, url))
        if final["season_year"] < last_season:
            events.append((pid, final["season_year"] + 1, "roster_exit", None, None, None,
                           f"last listed {final['season_year']}", final["source_url"]))
    return events


def build(df: pd.DataFrame, db_path=DB) -> dict:
    if db_path != ":memory:" and db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA.read_text())

    skipped = int(df.qa_flag.notna().sum())
    df = df[df.qa_flag.isna()].sort_values(["season_year", "last_name", "first_name"]).copy()
    years = sorted(int(y) for y in df.season_year.unique())
    con.executemany(
        "INSERT INTO seasons (season_year, label, conference, head_coach) VALUES (?, ?, 'SEC', ?)",
        [(y, str(y), head_coach(y)) for y in range(years[0], years[-1] + 1)],
    )

    pairs = candidate_pairs(df)
    to_player, confidence = resolve(df, pairs)
    df["player_id"] = df.sidearm_player_id.map(lambda s: to_player[int(s)])

    for pid, rows in df.groupby("player_id"):
        ids = sorted(int(s) for s in rows.sidearm_player_id.unique())
        con.execute(
            "INSERT INTO players (player_id, canonical_name, first_name, last_name, suffix, hometown, "
            "home_state, high_school, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (int(pid), latest(rows.raw_name), latest(rows.first_name), latest(rows.last_name),
             latest(rows.suffix), latest(rows.hometown_city), latest(rows.home_state),
             latest(rows.high_school),
             f"merged {len(ids)} Sidearm ids" if len(ids) > 1 else "single Sidearm id"),
        )
        for sid in ids:
            con.execute(
                "INSERT INTO player_aliases (player_id, alias_text, alias_type, source_name, confidence, notes) "
                "VALUES (?, ?, 'source_id', ?, ?, ?)",
                (int(pid), f"sidearm:{sid}", SOURCE, confidence.get(sid, 1.0),
                 "auto-merged on name + hometown/high school" if sid in confidence else None),
            )
        for name in rows.raw_name.unique():
            con.execute(
                "INSERT OR IGNORE INTO player_aliases (player_id, alias_text, alias_type, source_name, confidence) "
                "VALUES (?, ?, 'name', ?, 1.0)", (int(pid), name, SOURCE),
            )

    first_season = df.groupby("player_id").season_year.min()
    records = [{k: nn(v) for k, v in row.items()} for row in df.to_dict("records")]
    for row in records:
        is_first = row["season_year"] == first_season[row["player_id"]]
        status = "transfer_in" if row["previous_school"] and is_first else "active"
        con.execute(
            "INSERT INTO roster_entries (player_id, season_year, jersey_number, position, class_year, "
            "redshirt, height_inches, weight_lbs, status, source_name, source_url, snapshot_timestamp, raw_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(nn(row[k]) for k in (
                "player_id", "season_year", "jersey_number", "position", "class_year", "redshirt",
                "height_inches", "weight_lbs")) + (status,) + tuple(nn(row[k]) for k in (
                "source_name", "source_url", "snapshot_timestamp", "raw_name")),
        )
        if row["jersey_number"] is not None:
            con.execute(
                "INSERT OR IGNORE INTO player_aliases (player_id, alias_text, alias_type, season_year, "
                "source_name, confidence) VALUES (?, ?, 'jersey', ?, ?, 1.0)",
                (row["player_id"], str(int(row["jersey_number"])), row["season_year"], SOURCE),
            )

    events = career_events(records, years[-1])
    con.executemany(
        "INSERT INTO career_events (player_id, season_year, event_type, from_value, to_value, "
        "counterparty_school, notes, source_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [tuple(nn(v) for v in e) for e in events],
    )

    review = pairs[pairs.decision.str.startswith("review")] if len(pairs) else pairs
    for r in review.to_dict("records"):
        con.execute(
            "INSERT OR IGNORE INTO player_aliases (player_id, alias_text, alias_type, source_name, confidence, notes) "
            "VALUES (?, ?, 'source_id', ?, ?, ?)",
            (to_player[r["sidearm_id_a"]], f"sidearm:{r['sidearm_id_b']}", SOURCE, float(r["score"]),
             f"possible match with {r['name_b']} {r['seasons_b']} - needs manual review"),
        )
    con.commit()

    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("seasons", "players", "roster_entries", "player_aliases", "career_events")}
    con.close()
    return {
        "counts": counts,
        "qa_rows_skipped": skipped,
        "sidearm_ids": df.sidearm_player_id.nunique(),
        "decisions": pairs.decision.value_counts().to_dict() if len(pairs) else {},
        "pairs": pairs,
    }


def main() -> None:
    if not ROSTER_CLEAN.exists():
        raise SystemExit("run `python -m pipeline.clean` first")
    df = pd.read_csv(ROSTER_CLEAN, dtype={"snapshot_timestamp": str})
    df["jersey_number"] = df.jersey_number.astype("Int64")
    result = build(df)
    pairs = result["pairs"]
    pairs.sort_values(["decision", "score"], ascending=[True, False]).to_csv(REVIEW_QUEUE, index=False)

    c = result["counts"]
    print(f"skipped {result['qa_rows_skipped']} QA-flagged rows")
    print(f"entity resolution: {result['sidearm_ids']:,} Sidearm ids -> {c['players']:,} VolLineage players")
    print(f"  pair decisions: {result['decisions']}")
    for table, n in c.items():
        print(f"{table:<16}{n:>7,}")
    print(f"wrote {DB}")
    print(f"wrote {REVIEW_QUEUE}")


if __name__ == "__main__":
    main()
