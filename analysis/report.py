"""Coverage checks and first roster-transition metrics, straight from SQLite.

    python -m analysis.report

Writes CSV tables to reports/ and PNG charts to reports/figures/.
"""

from __future__ import annotations

import json
import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from paths import DB, FIGURES, REPORTS, ROSTER_RAW  # noqa: E402
from scrapers.fetch_rosters import load_manifest  # noqa: E402

COVERAGE_SQL = """
SELECT s.season_year,
       s.head_coach,
       COUNT(r.roster_entry_id)                         AS players_listed,
       MIN(r.snapshot_timestamp)                        AS snapshot_timestamp,
       ROUND(100.0 * AVG(r.height_inches IS NOT NULL), 1) AS pct_height,
       ROUND(100.0 * AVG(r.weight_lbs IS NOT NULL), 1)    AS pct_weight,
       ROUND(100.0 * AVG(r.class_year IS NOT NULL), 1)    AS pct_class,
       ROUND(100.0 * AVG(p.hometown IS NOT NULL), 1)      AS pct_hometown,
       ROUND(100.0 * AVG(p.high_school IS NOT NULL), 1)   AS pct_high_school,
       SUM(r.redshirt)                                  AS redshirt_labeled
FROM seasons s
LEFT JOIN roster_entries r ON r.season_year = s.season_year
LEFT JOIN players p ON p.player_id = r.player_id
GROUP BY s.season_year
ORDER BY s.season_year
"""

# Share of last season's roster that is listed again this season, plus arrivals.
RETENTION_SQL = """
WITH prev AS (
    SELECT cur.season_year,
           COUNT(*)                                    AS prev_roster,
           SUM(nxt.player_id IS NOT NULL)              AS returned
    FROM roster_entries prior
    JOIN seasons cur ON cur.season_year = prior.season_year + 1
    LEFT JOIN roster_entries nxt
           ON nxt.player_id = prior.player_id AND nxt.season_year = prior.season_year + 1
    GROUP BY cur.season_year
),
arrivals AS (
    SELECT season_year,
           SUM(event_type = 'roster_join')  AS newcomers,
           SUM(event_type = 'transfer_in')  AS transfers_in
    FROM career_events GROUP BY season_year
),
changes AS (
    SELECT season_year,
           SUM(event_type = 'jersey_change')   AS jersey_changes,
           SUM(event_type = 'position_change') AS position_changes
    FROM career_events GROUP BY season_year
)
SELECT s.season_year, s.head_coach, prev.prev_roster, prev.returned,
       ROUND(100.0 * prev.returned / prev.prev_roster, 1) AS retention_pct,
       a.newcomers, a.transfers_in, c.jersey_changes, c.position_changes
FROM seasons s
LEFT JOIN prev ON prev.season_year = s.season_year
LEFT JOIN arrivals a ON a.season_year = s.season_year
LEFT JOIN changes c ON c.season_year = s.season_year
ORDER BY s.season_year
"""

JERSEY_REUSE_SQL = """
SELECT jersey_number, COUNT(DISTINCT player_id) AS players_who_wore_it,
       MIN(season_year) AS first_season, MAX(season_year) AS last_season
FROM roster_entries WHERE jersey_number IS NOT NULL
GROUP BY jersey_number ORDER BY players_who_wore_it DESC, jersey_number LIMIT 10
"""

POSITION_SWITCH_SQL = """
SELECT from_value || ' -> ' || to_value AS switch, COUNT(*) AS n
FROM career_events WHERE event_type = 'position_change'
GROUP BY switch ORDER BY n DESC LIMIT 10
"""

LONGEST_CAREERS_SQL = """
SELECT p.canonical_name, COUNT(*) AS seasons, MIN(r.season_year) AS first, MAX(r.season_year) AS last,
       GROUP_CONCAT(DISTINCT r.jersey_number) AS jerseys, GROUP_CONCAT(DISTINCT r.position) AS positions
FROM roster_entries r JOIN players p USING (player_id)
GROUP BY r.player_id ORDER BY seasons DESC, last DESC LIMIT 8
"""


def capture_comparison() -> pd.DataFrame:
    """For seasons with several usable captures, do the captures list the same athletes?"""
    raw = pd.read_csv(ROSTER_RAW, dtype={"snapshot_timestamp": str})
    raw["athlete"] = (raw.first_name.fillna("") + " " + raw.last_name.fillna("")).str.lower().str.strip()
    rows = []
    for year, season in raw.groupby("season_year"):
        rosters = {ts: frozenset(g.athlete) for ts, g in season.groupby("snapshot_timestamp")}
        selected = season[season.selected_capture == 1].snapshot_timestamp.iloc[0]
        for ts, names in sorted(rosters.items()):
            rows.append({
                "season_year": year, "snapshot_timestamp": ts, "rows": int((season.snapshot_timestamp == ts).sum()),
                "distinct_athletes": len(names), "selected": ts == selected,
                "same_athletes_as_selected": names == rosters[selected],
                "only_in_this_capture": "; ".join(sorted(names - rosters[selected]))[:120],
                "missing_from_this_capture": "; ".join(sorted(rosters[selected] - names))[:120],
            })
    return pd.DataFrame(rows)


def manifest_summary() -> dict:
    entries = list(load_manifest().values())  # one entry per capture, even after --force re-fetches
    status = pd.Series([e["parse_status"] for e in entries]).value_counts().to_dict()
    return {"captures_fetched": len(entries), "bytes": sum(e["bytes"] for e in entries), "parse_status": status}


def plot(coverage: pd.DataFrame, transitions: pd.DataFrame) -> list[str]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    coaches = coverage.head_coach.unique()
    colors = dict(zip(coaches, plt.cm.tab10.colors))
    written = []

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(coverage.season_year, coverage.players_listed,
           color=[colors[c] for c in coverage.head_coach], label="players listed")
    later = transitions[transitions.season_year > transitions.season_year.min()]
    ax.plot(later.season_year, later.newcomers, "k.-", label="first appearance (newcomers)")
    for coach in coaches:
        ax.bar(0, 0, color=colors[coach], label=coach)
    ax.set_xlim(coverage.season_year.min() - 1, coverage.season_year.max() + 1)
    ax.set_title("Tennessee football: players listed per archived roster, 1998-2025")
    ax.set_xlabel("season")
    ax.set_ylabel("players")
    ax.legend(ncol=4, fontsize=8, loc="upper left")
    fig.tight_layout()
    path = FIGURES / "roster_size_by_season.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    written.append(path)

    t = transitions.dropna(subset=["retention_pct"])
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(t.season_year, t.retention_pct, color=[colors[c] for c in t.head_coach])
    for coach in coaches:
        ax.bar(0, 0, color=colors[coach], label=coach)
    ax.set_xlim(coverage.season_year.min(), coverage.season_year.max() + 1)
    ax.set_ylim(0, 100)
    ax.set_title("Year-over-year retention: % of last season's roster listed again")
    ax.set_xlabel("season")
    ax.set_ylabel("% retained")
    ax.legend(ncol=3, fontsize=8, loc="lower left")
    fig.tight_layout()
    path = FIGURES / "retention_by_season.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    written.append(path)

    fig, ax = plt.subplots(figsize=(11, 4.5))
    a = transitions[transitions.season_year > transitions.season_year.min()]
    ax.bar(a.season_year, a.newcomers - a.transfers_in, color="#9bb7d4", label="new, no previous school listed")
    ax.bar(a.season_year, a.transfers_in, bottom=a.newcomers - a.transfers_in, color="#ff8200",
           label="new, previous school listed (transfer / JUCO)")
    ax.axvline(2018.5, color="gray", ls="--", lw=1)
    ax.text(2018.6, ax.get_ylim()[1] * 0.92, "NCAA transfer portal opens (Oct 2018)", fontsize=8, color="gray")
    ax.set_title("Roster arrivals per season (first appearance on a recovered roster)")
    ax.set_xlabel("season")
    ax.set_ylabel("players")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    path = FIGURES / "arrivals_by_season.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    written.append(path)
    return [str(p) for p in written]


def main() -> None:
    if not DB.exists():
        raise SystemExit("run `python -m pipeline.load` first")
    REPORTS.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    coverage = pd.read_sql(COVERAGE_SQL, con)
    transitions = pd.read_sql(RETENTION_SQL, con)
    jerseys = pd.read_sql(JERSEY_REUSE_SQL, con)
    switches = pd.read_sql(POSITION_SWITCH_SQL, con)
    careers = pd.read_sql(LONGEST_CAREERS_SQL, con)
    con.close()
    captures = capture_comparison()

    coverage.to_csv(REPORTS / "season_coverage.csv", index=False)
    transitions.to_csv(REPORTS / "season_transitions.csv", index=False)
    jerseys.to_csv(REPORTS / "jersey_reuse_top10.csv", index=False)
    switches.to_csv(REPORTS / "position_switches_top10.csv", index=False)
    captures.to_csv(REPORTS / "capture_comparison.csv", index=False)

    pd.set_option("display.width", 160)
    m = manifest_summary()
    print(f"== Archive: {m['captures_fetched']} Wayback captures fetched "
          f"({m['bytes'] / 1e6:.1f} MB raw HTML); parse status {m['parse_status']}")
    seasons_with_rows = int((coverage.players_listed > 0).sum())
    print(f"== Coverage: {seasons_with_rows}/{len(coverage)} seasons recovered, "
          f"{int(coverage.players_listed.sum()):,} roster rows")
    print(coverage[["season_year", "head_coach", "players_listed", "snapshot_timestamp",
                    "pct_hometown", "pct_high_school", "pct_weight", "redshirt_labeled"]].to_string(index=False))

    multi = captures.groupby("season_year").filter(lambda g: len(g) > 1)
    disagree = multi[~multi.same_athletes_as_selected]
    print(f"\n== Capture agreement: {multi.season_year.nunique()} seasons have 2+ usable captures; "
          f"{disagree.season_year.nunique()} seasons have captures listing different athletes")
    if len(disagree):
        print(disagree.to_string(index=False))

    print("\n== Transitions (retention = % of previous roster listed again)")
    print(transitions.to_string(index=False))
    era = transitions.dropna(subset=["retention_pct"]).groupby("head_coach", sort=False).agg(
        seasons=("season_year", "count"), avg_retention_pct=("retention_pct", "mean"),
        avg_newcomers=("newcomers", "mean"), avg_transfers_in=("transfers_in", "mean"),
    ).round(1)
    era.to_csv(REPORTS / "transitions_by_coach.csv")
    print("\n== By head coach (seasons after the first recovered roster)")
    print(era.to_string())
    print("\n== Most reused jersey numbers")
    print(jerseys.to_string(index=False))
    print("\n== Most common position switches")
    print(switches.to_string(index=False))
    print("\n== Longest listed careers")
    print(careers.to_string(index=False))

    print("\nwrote reports/*.csv")
    for path in plot(coverage, transitions):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
