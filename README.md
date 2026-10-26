# VolLineage

**Historical Tennessee Football Roster Archive & Roster Transition Analysis**

Course project for COSC 445 (Digital Archaeology), University of Tennessee, Knoxville.

Team: Hien Vo, Hamzah, Bansari.

VolLineage recovers University of Tennessee football rosters from 1998 to the present, turns fragmented web archives into a normalized player history, and measures how those rosters actually changed: jersey reuse, position switches, redshirt years, and transfer-portal movement.

## Motivation

UTSports roster pages were built for a single season, then replaced. Layouts, table markup, and player labels drifted every few years. Many seasons survive only as Internet Archive snapshots, and those snapshots are incomplete, duplicated, and parsed differently by each capture. A jersey number is not an identity. The same athlete can appear under a spelling variant, a new number, a new position, or a redshirt designation, and later leave or arrive through the transfer portal with no stable key linking the rows.

Digital archaeology here means treating those pages as artifacts: record where each row came from, keep the raw capture, and only then resolve it to a person and a season. The archive is the product. The charts come after the chain of custody is intact.

## Problem statement

The project has four concrete recovery problems:

1. **Fragmented HTML.** Roster tables from the late 1990s through the modern site do not share a schema. Columns move, headers change, and some captures are image-heavy or JavaScript-rendered.
2. **Uneven survival.** Wayback Machine captures cluster around redesigns and big seasons. Adjacent years can be missing, truncated, or stored as a different URL path on `utsports.com`.
3. **Identifier drift.** Names, jersey numbers, positions, class years, and redshirt flags change independently. Numbers are recycled. Portal-era arrivals and departures are often absent from the school roster page that should have recorded them.
4. **No durable store.** Scraped rows in a spreadsheet collapse identity and season state into one record, so a later correction overwrites provenance. VolLineage separates the person (`players`) from the season appearance (`roster_entries`) and from the name or number variants used to match them (`player_aliases`).

## Pipeline

```
Ingestion  ->  Entity resolution  ->  Relational SQLite  ->  Analysis / UI
scrapers/     pipeline/              db/                   analysis/  (+ web/)
data/raw/     data/processed/
```

1. **Ingestion.** Spiders fetch Wayback CDX results for historical UTSports football roster URLs and, where a page is missing or unreadable, a secondary public season summary. Raw HTML and the capture metadata (URL, timestamp, status) land in `data/raw/` and stay out of git.
2. **Entity resolution.** Extractors emit one candidate row per listed athlete. Normalization folds whitespace, suffixes, and position abbreviations. Deduplication proposes a `player_id` from name, hometown, high school, and career overlap, then records rejected or low-confidence aliases instead of silently merging them. Season-only facts (number, position, class, redshirt, height, weight) stay on the roster entry.
3. **Relational storage.** `db/schema.sql` loads into a local SQLite file. Static identity, season appearance, alias evidence, and career events (join, exit, position change, jersey change, transfer) are separate tables so a correction does not destroy the source row.
4. **Analysis and presentation.** SQL and pandas reports in `analysis/` check coverage by season, flag unresolved duplicates, and compute transition metrics (retention, portal inflow and outflow, position change rate, jersey churn). A Next.js visualizer under `web/` is a later milestone and is not part of this scaffold.

## Data sources

| Source | Role | Notes |
| --- | --- | --- |
| Wayback Machine snapshots of UTSports football rosters | Primary archive, 1998–present | Prefer CDX API plus saved HTML over live re-crawls. Store capture timestamp and original URL with every row. |
| Sports-Reference College Football | Cross-check for missing or broken school pages | Use public season roster and player pages to fill gaps and to challenge a proposed identity match. |
| Public transfer-portal tracking | Portal-era arrivals and departures | School rosters often omit the exit. Record the other school and season on `career_events` when a public listing supports it. |

Crawl politely: identify the project in the User-Agent, respect `robots.txt`, and rate-limit. Prefer an existing Wayback capture to a fresh hit on the live site.

## Repository layout

```
.
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/                 # gitignored HTML, CDX JSON, and scrape logs
│   └── processed/           # gitignored normalized JSON/CSV extracts
├── scrapers/                # archive discovery and HTML extraction
├── pipeline/                # normalize, dedupe, and resolve player identity
├── db/
│   └── schema.sql           # players, seasons, roster_entries, player_aliases, career_events
├── analysis/                # coverage checks, transition metrics, player lineage lookup
├── reports/                 # generated CSV tables and figures (committed)
├── tests/                   # scraper fixtures and resolution cases
├── paths.py                 # shared file locations
├── Makefile                 # pipeline shortcuts
└── web/                     # planned Next.js / Tailwind visualizer
```

## Quickstart

Requires Python 3.11 or newer and network access to `web.archive.org`.

```bash
make setup          # python3 -m venv .venv && pip install -r requirements.txt
make pipeline       # discover -> fetch-all -> extract -> clean -> load -> report (about 3-4 minutes)
make test
```

Each stage can also be run on its own, in order:

| Command | Output |
| --- | --- |
| `python -m scrapers.discover` | `data/raw/cdx/season_captures.json`: Wayback CDX captures of `utsports.com/sports/football/roster/YYYY`, 1998–2025 |
| `python -m scrapers.fetch_rosters --all-captures` | `data/raw/html/*.html` and `data/raw/manifest.jsonl` (one provenance line per capture) |
| `python -m scrapers.extract` | `data/processed/roster_raw.csv`: every player row from every usable capture |
| `python -m pipeline.clean` | `data/processed/roster_clean.csv`: one capture per season, normalized fields, QA flags |
| `python -m pipeline.load` | `db/vollineage.sqlite3` and `data/processed/review_queue.csv` |
| `python -m analysis.report` | `reports/*.csv` and `reports/figures/*.png` |
| `python -m analysis.lineage "Jauan Jennings"` | one athlete's resolved history with provenance |
| `python -m scrapers.discover --inventory` | capture counts for every site era |

Use the `.venv/bin/python` interpreter (or `source .venv/bin/activate`) and run from the repository root. The fetcher is resumable: cached captures are not downloaded again unless `--force` is passed. Copy `.env.example` to `.env` to set the User-Agent sent to the Internet Archive. Do not commit `.env`.

The database, raw HTML, and processed CSVs are gitignored and rebuilt by the pipeline. `reports/` is committed so the current results are visible without a rebuild.

`playwright` is optional and is not pinned in `requirements.txt`. Add it only if a roster year cannot be read from saved HTML.

## Current status (Progress Check 1)

See [`docs/progress_check_1_demo_guide.md`](docs/progress_check_1_demo_guide.md) for the demo script, current numbers, risks, and next steps.

## Team assignments

| Member | Workstream | Owns |
| --- | --- | --- |
| Hien Vo | Entity resolution and storage | `pipeline/`, `db/schema.sql`, match review rules, load into SQLite |
| Hamzah | Ingestion | Wayback CDX discovery, UTSports extractors, raw capture layout in `data/raw/` |
| Bansari | Analysis and presentation | Coverage and transition queries in `analysis/`, later `web/` visualizer |

Sports-Reference reconciliation is shared: Hamzah lands the raw comparison rows, Hien Vo decides whether they merge, and Bansari reports seasons that still disagree.

## Milestone roadmap

1. **Source inventory and schema freeze.** List roster URL patterns by era, confirm the SQLite tables, and agree on the fields a scraper must emit.
2. **Pilot extract.** Parse one early HTML era and one modern era end to end into `data/processed/`, with capture metadata attached.
3. **Resolution prototype.** Cluster pilot rows into `players` and `player_aliases`, and record uncertain matches for manual review.
4. **Backfill.** Run 1998–present, then fill holes from Sports-Reference and portal listings. Every inserted roster row keeps `source_name`, `source_url`, and `snapshot_timestamp`.
5. **Validation.** Publish season coverage, duplicate-name report, and jersey or position conflicts before any chart is treated as final.
6. **Transition analysis and UI.** Retention, portal flow, and position-change metrics, then the Next.js visualizer.


