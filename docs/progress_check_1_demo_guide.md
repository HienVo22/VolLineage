# VolLineage: Progress Check 1 demo guide

## 1. Setup and dependencies

Do this once on each laptop that will run the demo.

### Requirements

| Dependency | Version | Check | Install (macOS) |
| --- | --- | --- | --- |
| Python | 3.11 or newer | `python3 --version` | [python.org](https://www.python.org/downloads/) or `brew install python@3.12` |
| git | any | `git --version` | `xcode-select --install` |
| make | any | `make --version` | `xcode-select --install` |
| sqlite3 CLI | 3.33 or newer (for `-box` output) | `sqlite3 --version` | preinstalled on macOS; otherwise `brew install sqlite` |
| Internet access | `web.archive.org` reachable | `curl -sI https://web.archive.org \| head -1` | — |

Python packages (installed by `make setup` from `requirements.txt`): `requests`, `beautifulsoup4`, `pandas`, `sqlite-utils`, `pytest`, `python-dotenv`, `matplotlib`.

### Install

```bash
git clone https://github.com/HienVo22/VolLineage.git
cd VolLineage
make setup                   # creates .venv and installs requirements.txt
cp .env.example .env         # optional: put your utk.edu email in the User-Agent
```

Without `make`, run the equivalent by hand:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Build the data (required before the demo)

The raw HTML, processed CSVs, and SQLite database are not in git, so each laptop must build them once:

```bash
make pipeline                # discover -> fetch -> extract -> clean -> load -> report (about 3-4 minutes)
make test                    # should print: 28 passed
```

Every command in this guide runs from the repository root, inside the virtual environment (`source .venv/bin/activate`).

---

## 2. Numbers to know

| What | Value |
| --- | --- |
| Source | Internet Archive (Wayback Machine) captures of `utsports.com/sports/football/roster/YYYY` |
| Seasons covered | **28 of 28** (1998–2025) |
| Captures downloaded | **87** (77 MB of HTML); **79** parse, **8** are from UT's new 2025+ site and don't |
| Player rows | **8,610** raw rows from all captures; **3,020** roster rows after picking one capture per season |
| Format | Raw HTML, then CSV (`data/processed/`), then SQLite (`db/vollineage.sqlite3`) |
| Football captures that exist across all 4 old site versions | about **46,000** (the proposal said 49,177; see Risks) |

---

## 3. Before class

1. Everyone runs through section 1 so `make pipeline` and `make test` both work.
2. Open a terminal in the repo root, run `source .venv/bin/activate`, and make the font large (Cmd and +).
3. Open `reports/figures/arrivals_by_season.png` so you can switch to it quickly.
4. Check the Wi-Fi: `curl -sI https://web.archive.org | head -1` should print `HTTP/2 200`.

**If the Wi-Fi or the Wayback Machine is down:** skip the live fetch. Everything else runs from the cached HTML. Say: "The fetcher caches every capture, so we can rebuild offline," and run `make extract clean load` instead.

---

## 4. The five-minute script

The five parts follow the assignment's order. Speakers are suggestions; everyone should be able to explain every part.

### 1) Project status, 0:00–0:45 (Hien)

> "VolLineage recovers every Tennessee football roster from 1998 to today from the Internet Archive, so we can follow each player across seasons and measure roster turnover across coaching eras: retention, transfers, jersey numbers, and position changes.
>
> **Done:** we found the archived roster pages, wrote a script that downloads them, and parsed every season into a CSV and a SQLite database.
> **In progress:** linking each player's seasons into one identity, and cleaning up inconsistencies between seasons."

### 2) Data collected, 0:45–1:45 (Hamzah)

> "The **source** is the Wayback Machine. Its CDX API lists every saved copy of a URL. UT's current site has one roster page per season, and the archive has 1 to 5 copies of each, so we downloaded all **87** copies, 77 MB of HTML, covering **all 28 seasons**."

Show the **format**: each download is logged with where it came from.

```bash
head -n 2 data/raw/manifest.jsonl | tail -n 1 | python -m json.tool
```

> "Each line records the original URL, the Wayback timestamp, a content hash, and whether it parsed. The roster data is JSON hidden inside a script tag on each page, and we extract it into one row per player."

Show **how much** data there is, and what a row looks like:

```bash
wc -l data/processed/roster_raw.csv data/processed/roster_clean.csv
sqlite3 -box db/vollineage.sqlite3 "SELECT season_year, raw_name, jersey_number AS jersey, position, class_year, redshirt, height_inches, weight_lbs, snapshot_timestamp FROM roster_entries WHERE season_year = 2024 LIMIT 5;"
```

> "8,610 player rows across all copies, and 3,020 once we keep one copy per season. Each row keeps the Wayback timestamp it came from."

### 3) Live evidence, 1:45–3:15 (Hamzah, then Bansari)

**Live retrieval (about 10 seconds):**

```bash
python -m scrapers.discover --start 2024 --end 2024
python -m scrapers.fetch_rosters --seasons 2024 --force
```

Expected output:

```
2024 20250807211446  fetched  no_roster_json     0 players    2383 KB
2024 20241214044724  fetched  ok               123 players     928 KB
```

> "That's a live request to the Wayback Machine. The newest copy of the 2024 page was saved after UT switched website platforms, and it has no roster data. The script detects that and falls back to the December 2024 copy, which has all 123 players."

**Run a query (Bansari):**

```bash
sqlite3 -box db/vollineage.sqlite3 "SELECT season_year, COUNT(*) AS players, SUM(status = 'transfer_in') AS arrived_from_another_school FROM roster_entries WHERE season_year >= 2016 GROUP BY 1;"
```

**Show one early chart (Bansari):** open `reports/figures/arrivals_by_season.png`.

> "This is a first look, not a result yet. Each bar is the number of players appearing on the roster for the first time; orange means they listed a previous school. That share grows after the NCAA transfer portal opened in 2018 and peaks in 2021. We still have to check this against real transfer-portal data."

### 4) Problems and risks, 3:15–4:15 (Hien)

1. **The site's own player IDs aren't reliable.** Older seasons were re-entered with new IDs, so the same player can have two IDs. We have to link players ourselves using name, hometown, and high school.
2. **Copies of the same page disagree.** In 4 seasons, different Wayback copies list different players; for example, the July 2022 copy lists 124 players and later copies list 117. We keep every copy and pick one per season with a fixed rule.
3. **Older rosters are thinner.** Rosters before 2009 list about 90–100 players versus about 120 now, and have no redshirt labels before 2005.
4. **UT's new website (late 2025)** doesn't embed the roster data, so 2026 will need a new parser.
5. **Correction to the proposal:** we said about 49,000 captures, but one count included every sport. Football-only is about 46,000. This doesn't change the plan.

### 5) Next steps, 4:15–5:00 (Bansari)

> "Next: finish linking players across seasons and check the matches by hand on a sample, add transfer-portal and FBS data from the CollegeFootballData API for comparison, and parse one older site version to cross-check the early seasons. Then the retention and transfer analysis by coaching era for the final report."

---

## 5. Backup: only if asked

These are already built. Don't show them unless the TA or professor asks.

**"How do you know two rows are the same player?"**

```bash
python -m analysis.lineage "Jauan Jennings"
```

He had two site IDs (2015–16 and 2018–19). We link IDs only when the name matches exactly, the hometown or high school matches, nothing contradicts, they never appear on the same roster, and the career fits in six seasons. 1,199 site IDs become 1,146 players. Uncertain pairs go to `data/processed/review_queue.csv` instead of being merged. Many of those come from typos in the source pages, such as "Nasvhille" and "Eerie" for Erie.

**"What cleaning have you done?"** Run `python -m pipeline.clean`. It folds class labels ("R-So." becomes SO plus a redshirt flag) and state names ("Tenn.", "Tennessee", and "T.N." all become TN), and it flags odd rows instead of deleting them.

**"Any other analysis?"** Run `python -m analysis.report | head -40`, or open `reports/figures/retention_by_season.png`. Retention is about 60–70% in every era so far.

**"How much exists across all the old site versions?"** Run `python -m scrapers.discover --inventory`. It takes about 7 seconds and totals 46,093 captures.

**"How do you know which season a page describes?"** The year comes from the URL. The parser also reads the season stored in the page and rejects the copy if the two disagree.

**"How do you count a transfer?"** For now, a player whose first roster lists a previous school. That includes junior colleges, so it's an upper bound until we add the portal data.

**"Are you redistributing the HTML?"** No. Raw pages stay local and are gitignored; only code and derived reports are in the repo.

---

## 6. Instructions for the TA or professor

Requirements and installation are in section 1. In short:

```bash
git clone https://github.com/HienVo22/VolLineage.git
cd VolLineage
make setup        # creates .venv and installs requirements.txt
make test         # 28 unit tests: extractor, normalization, entity resolution
make pipeline     # full rebuild from the Wayback Machine, about 3-4 minutes
```

Individual steps, in order:

```bash
.venv/bin/python -m scrapers.discover                      # CDX lookup per season
.venv/bin/python -m scrapers.fetch_rosters --all-captures  # download and cache every capture
.venv/bin/python -m scrapers.extract                       # HTML -> data/processed/roster_raw.csv
.venv/bin/python -m pipeline.clean                         # normalize -> data/processed/roster_clean.csv
.venv/bin/python -m pipeline.load                          # SQLite -> db/vollineage.sqlite3
.venv/bin/python -m analysis.report                        # reports/*.csv and reports/figures/*.png
.venv/bin/python -m analysis.lineage "Hardesty"            # any player name or part of one
.venv/bin/python -m scrapers.discover --inventory          # capture counts per site era
```

Queries to try on the database:

```bash
# Roster size and transfer arrivals per season
sqlite3 -box db/vollineage.sqlite3 "SELECT season_year, COUNT(*) players, SUM(status='transfer_in') transfers_in FROM roster_entries GROUP BY 1;"

# Every athlete who wore #16, with the capture each row came from
sqlite3 -box db/vollineage.sqlite3 "SELECT season_year, raw_name, position, snapshot_timestamp FROM roster_entries WHERE jersey_number = 16 ORDER BY 1;"
```

Where things are:

| Path | Contents |
| --- | --- |
| `scrapers/` | Wayback discovery, resumable download, and the roster extractor |
| `pipeline/` | Field cleaning and the SQLite load |
| `analysis/` | Report queries, charts, and the player lookup |
| `db/schema.sql` | `seasons`, `players`, `player_aliases`, `roster_entries`, `career_events` |
| `reports/` | Generated tables and figures from the current run |
