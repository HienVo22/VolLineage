"""Compare the roster previous-school proxy with the CollegeFootballData portal list.

    python -m analysis.portal_compare

Reads db/vollineage.sqlite3 and data/processed/cfbd_portal_tennessee.csv.
Writes reports/portal_vs_proxy.csv and reports/figures/portal_vs_proxy.png.
Portal names are not matched to VolLineage players. Withdrawn portal entries are excluded
from the counts.
"""

from __future__ import annotations

import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from paths import DB, FIGURES, PORTAL_COMPARE, PORTAL_CSV, PORTAL_FIGURE  # noqa: E402

PROXY_SQL = """
SELECT season_year, SUM(status = 'transfer_in') AS roster_previous_school
FROM roster_entries
WHERE season_year BETWEEN ? AND ?
GROUP BY season_year
ORDER BY season_year
"""


def portal_counts(portal: pd.DataFrame) -> pd.DataFrame:
    active = portal[portal.eligibility.fillna("") != "Withdrawn"]
    grouped = active.groupby("season_year").agg(
        portal_arrivals=("direction", lambda s: int((s == "in").sum())),
        portal_departures=("direction", lambda s: int((s == "out").sum())),
    )
    return grouped.reset_index()


def comparison_table(portal: pd.DataFrame) -> pd.DataFrame:
    years = sorted(int(y) for y in portal.season_year.unique())
    with sqlite3.connect(DB) as con:
        proxy = pd.read_sql(PROXY_SQL, con, params=(years[0], years[-1]))
    counts = portal_counts(portal)
    table = pd.DataFrame({"season_year": years}).merge(proxy, how="left").merge(counts, how="left")
    for column in ("roster_previous_school", "portal_arrivals", "portal_departures"):
        table[column] = table[column].fillna(0).astype(int)
    return table


def plot(table: pd.DataFrame) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    width = 0.38
    positions = range(len(table))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([p - width / 2 for p in positions], table.roster_previous_school, width,
           label="Roster lists a previous school", color="#9bb7d4")
    ax.bar([p + width / 2 for p in positions], table.portal_arrivals, width,
           label="Portal destination is Tennessee", color="#ff8200")
    start, end = int(table.season_year.min()), int(table.season_year.max())
    span = str(start) if start == end else f"{start}-{end}"
    ax.set_xticks(list(positions), [str(y) for y in table.season_year])
    ax.set_title(f"Tennessee arrivals, {span}: roster field vs portal list")
    ax.set_xlabel("season")
    ax.set_ylabel("players")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PORTAL_FIGURE, dpi=150)
    plt.close(fig)


def main() -> None:
    if not DB.exists():
        raise SystemExit("missing db/vollineage.sqlite3. Run `make pipeline` first.")
    if not PORTAL_CSV.exists():
        raise SystemExit("missing portal CSV. Run `python -m scrapers.cfbd` first.")
    portal = pd.read_csv(PORTAL_CSV)
    table = comparison_table(portal)
    table.to_csv(PORTAL_COMPARE, index=False)
    plot(table)
    print(table.to_string(index=False))
    print(f"\nwrote {PORTAL_COMPARE}")
    print(f"wrote {PORTAL_FIGURE}")
    print("These counts are not linked to player ids. A portal row and a roster row can be the same person or not.")


if __name__ == "__main__":
    main()
