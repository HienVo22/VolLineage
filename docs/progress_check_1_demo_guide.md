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
| Seasons recovered | **28 of 28** (1998–2025), one Wayback capture selected per season |
| Wayback captures downloaded | **87** unique captures (77 MB raw HTML); **79** parse, **8** rejected (new 2025+ site template) |
| Raw player rows (all captures) | **8,610** in `data/processed/roster_raw.csv` |
| Roster rows in the database | **3,020** (`roster_entries`), after 2 QA-flagged duplicate listings were skipped |
| Identity resolution | **1,199** Sidearm site IDs resolved to **1,146** players: **57** auto-merges, **16** pairs in the manual review queue |
| Other tables | **5,383** `player_aliases`, **2,836** `career_events`, **28** `seasons` |
| Total archive surface (CDX inventory, 4 site eras) | **46,093** unique football-section captures (the proposal said 49,177; see the correction under Risks) |
| Tests | **28** passing (`make test`) |

Early results (preliminary, roster-page data only):

- Year-over-year retention has stayed around **58–71%** in every era: about 66% under Fulmer and about 63% under Heupel.
- Arrivals with a previous school listed rose from about **3 per season under Fulmer to about 13 under Heupel**, with a peak of 18 in 2021 (the year the one-time transfer rule took effect).
- The most common "position switches" (RB to TB, OL to OG) are partly **label drift**: the site renamed positions between eras, so a crosswalk is needed before reporting position changes.

---

## 3. Before class

### The night before

Complete section 1, then run `make pipeline` and `make test` once more to confirm everything still works. Once the HTML is cached, reruns take seconds.

### Ten minutes before the demo

1. Open **two terminal tabs** in the repo root and run `source .venv/bin/activate` in both.
2. Make the terminal font large (Cmd and + a few times).
3. Open these in Preview or the editor so you can switch to them instantly:
   - `reports/figures/roster_size_by_season.png`
   - `reports/figures/arrivals_by_season.png`
   - `reports/figures/retention_by_season.png`
   - `data/processed/review_queue.csv` (in the editor or a spreadsheet)
4. Check the Wi-Fi: `curl -sI https://web.archive.org | head -1` should print `HTTP/2 200`.

### If the Wi-Fi or the Wayback Machine is down

Skip step a ("Live retrieval") in section 4. Everything else runs offline from the cached HTML. Say: "The fetcher is resumable and caches every capture, so we can rebuild the whole database offline," then run `make extract clean load` to show it.

---

## 4. The five-minute script

### 0:00–0:45. Project status (Hien)

> "VolLineage recovers every Tennessee football roster from 1998 to today from the Internet Archive and tracks each athlete across seasons, even though jersey numbers, positions, class labels, and name spellings all change. Then we measure roster turnover: retention, transfers, jersey reuse, and position changes across coaching eras.
>
> **Done:** Wayback discovery, a resumable fetcher, an extractor for the Sidearm-era pages, cleaning, a SQLite database with provenance on every row, a first entity-resolution pass, and a first analysis report.
> **In progress:** improving entity resolution with fuzzy hometown matching and a hand-labeled gold set, extractors for the older site eras, and FBS comparison data."

### 0:45–1:45. Data collected (Hamzah)

Show the source in the terminal:

```bash
python -m scrapers.discover --inventory
```

That takes about 7 seconds and prints the 4 site eras, 46,093 captures in total.

> "The **source** is the Internet Archive. We query its **CDX API**, which lists every saved copy of a URL, then download the exact archived bytes through the `id_` endpoint. The athletics site moved through four platforms, and this is how many captures survive from each.
>
> We found that the current Sidearm site has one page per season, `/sports/football/roster/1998` through `/2025`, and the Wayback Machine has 1–5 captures of each. We downloaded all **87**, which is 77 MB of HTML."

Show the **format** with one provenance record:

```bash
head -n 2 data/raw/manifest.jsonl | python -m json.tool --json-lines | head -30
```

> "Every capture gets a manifest line: original URL, Wayback timestamp, content hash, file path, and whether it parsed. Every row in the database carries the URL and capture timestamp it came from."

Then the size of the data:

```bash
wc -l data/processed/roster_raw.csv data/processed/roster_clean.csv
sqlite3 -box db/vollineage.sqlite3 "SELECT 'players', COUNT(*) FROM players UNION ALL SELECT 'roster_entries', COUNT(*) FROM roster_entries UNION ALL SELECT 'player_aliases', COUNT(*) FROM player_aliases UNION ALL SELECT 'career_events', COUNT(*) FROM career_events;"
```

> "8,610 raw player rows across all captures. After picking one capture per season, that's 3,020 roster rows and 1,146 distinct players."

### 1:45–3:30. Live evidence (Hamzah, then Hien, then Bansari)

**a. Live retrieval (Hamzah, about 10 seconds):**

```bash
python -m scrapers.discover --start 2024 --end 2024
python -m scrapers.fetch_rosters --seasons 2024 --force
```

Expected output:

```
2024 20250807211446  fetched  no_roster_json     0 players    2383 KB
2024 20241214044724  fetched  ok               123 players     928 KB
```

> "This is a live request to the Wayback Machine. The newest 2024 capture is from August 2025, after UT moved to a new website platform, and it has no roster data in it. The fetcher detects that and falls back to the December 2024 capture, which has all 123 players. The roster is embedded as JSON inside a script tag, so we parse that rather than the visible HTML."

**b. Rebuild and resolve (Hien, about 3 seconds):**

```bash
python -m scrapers.extract && python -m pipeline.clean && python -m pipeline.load
```

Point at these lines in the output:

- `class labels 9 raw variants -> 5 codes (+ redshirt flag ...)`: "R-So." becomes class SO with redshirt = 1.
- `hometown state 75 raw variants -> 42 values`: "Tenn.", "Tennessee", "TN", and "T.N." all become TN.
- `entity resolution: 1,199 Sidearm ids -> 1,146 VolLineage players`

> "We expected the site's own player ID to be a stable key. It isn't: seasons that were back-filled into the new site got new IDs, so one athlete can have two or three. We merge two IDs automatically only when the name matches exactly, the hometown or high school matches, nothing contradicts, they're never on the same roster, and the career fits in six seasons. Anything weaker goes to a review queue instead of being merged."

```bash
python -m analysis.lineage "Jauan Jennings"
```

> "Jauan Jennings had two site IDs, one for 2015–16 and one for 2018–19. We merged them on name, Murfreesboro, and Blackman High School. The 2017 gap is flagged as a career event. The archived 2017 roster doesn't list him, which matches his 2017 injury and dismissal, so the gap is real history, not a scraper bug."

Show the review queue (`data/processed/review_queue.csv`, rows whose `decision` is `review` or `review_conflicting_fields`):

> "These are the cases we won't auto-merge. Look at the source typos: 'Nasvhille', 'Eerie' for Erie, 'Rverdale', 'Deanthoine' vs 'Deanthonie'. These are the digital-archaeology problems, and they're what our next matching step targets."

**c. Preliminary analysis (Bansari, about 45 seconds):**

```bash
python -m analysis.report | head -40
```

Then switch to the figures:

- `roster_size_by_season.png`: "Every season is recovered. Before 2009 the back-filled rosters list about 90–100 players versus about 115–125 recently, so older seasons are probably partial, and we treat them that way."
- `arrivals_by_season.png`: "Orange is new arrivals with a previous school listed. It grows after the transfer portal opened in October 2018 and peaks in 2021, when the one-time transfer rule took effect."
- `retention_by_season.png`: "Retention is about 60–70% in every era. So far, more players arriving through transfers has not meant lower retention."

### 3:30–4:15. Problems and risks (Hien)

1. **The site's own IDs aren't stable.** Back-filled seasons have different IDs, so we have to do entity resolution ourselves; we can't rely on theirs.
2. **Archived pages change over time.** Captures of the *same* URL disagree in 4 seasons. The July 2022 capture lists 124 athletes, and 2023+ captures list 117 with different names. 2009 and 2015 captures garble names ("Darren Jr." vs "Darren Myles Jr."). We store every capture and choose one with a documented rule (most real athletes, newest on ties). See `reports/capture_comparison.csv`.
3. **Older rosters are incomplete.** 1998–2008 back-fills list about 90–100 players, have no redshirt labels before 2005, and about 400 rows give only a bare city ("Knoxville") with no state.
4. **New platform in late 2025.** UT's new site has no embedded roster JSON, so 2026 needs a new extractor. 8 captures already fail for this reason.
5. **Correction to the proposal.** We said 3,208 `roster.aspx` captures; that count included every sport. Football-only is 124, so the true total is about 46,000, not 49,000. This doesn't affect the plan, because the per-season pages cover every year.
6. **Data artifacts.** One 2010 capture lists "Rosalia Alda" 8 times with no jersey or position, apparently a record from another sport. We flag artifacts like this with a QA flag rather than deleting them, and the capture-selection rule avoids that capture.

### 4:15–5:00. Next steps (Bansari)

> "Next week: fuzzy hometown and high-school matching to clear the review queue, and a hand-labeled gold set of about 200 pairs to measure precision and recall. Hamzah adds the CollegeFootballData API for FBS and portal baselines, plus one legacy-era extractor (CollegeSports, 2004–08) to cross-check our back-filled seasons. Then a position crosswalk, so RB-to-TB isn't counted as a real switch, and the final charts by coaching era. The web viewer is a stretch goal."

---

## 5. Likely questions

**Why the Sidearm season pages instead of scraping each old site?**
They cover all 28 seasons with one extractor and carry hometown, high school, height, and weight. The older platforms are still in scope as a cross-check, because they are closer to what was actually published at the time.

**How do you know which season a page describes?**
The season comes from the URL (`/roster/2013`). The extractor also reads the season embedded in the page JSON and rejects the capture as `season_mismatch` if they disagree.

**Why not just merge everyone with the same name?**
There are 3 pairs of different athletes with the same name on the *same* roster, and 2 same-name pairs whose combined careers span more than 6 seasons. Name alone over-merges.

**How do you count a transfer?**
For now, an athlete whose first recovered roster lists a `previous_school`. That includes JUCO and prep schools, so it's an upper bound until we add the portal data from the API.

**How long does a full rebuild take?**
About 3–4 minutes from scratch, mostly polite rate limiting of 1.5 seconds per request. It takes seconds when the HTML is cached.

**Are you redistributing the HTML?**
No. Raw captures stay local and are gitignored. The code, schema, and derived reports are in the repo.

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

# Players formed by merging more than one Sidearm id
sqlite3 -box db/vollineage.sqlite3 "SELECT canonical_name, notes FROM players WHERE notes LIKE 'merged%' LIMIT 15;"

# Identity links waiting for manual review
sqlite3 -box db/vollineage.sqlite3 "SELECT p.canonical_name, a.alias_text, a.confidence, a.notes FROM player_aliases a JOIN players p USING (player_id) WHERE a.notes LIKE '%review%';"
```

Where things are:

| Path | Contents |
| --- | --- |
| `scrapers/wayback.py` | CDX client and raw-capture fetcher (rate limit, retries, gzip handling) |
| `scrapers/discover.py`, `scrapers/fetch_rosters.py` | Capture discovery; resumable download with manifest and fallback |
| `scrapers/sidearm.py`, `scrapers/extract.py` | Embedded-JSON extractor; per-season capture selection |
| `pipeline/normalize.py`, `pipeline/clean.py` | Field cleaning (class, redshirt, state, position, size) and QA flags |
| `pipeline/load.py` | SQLite load, entity resolution rules, career events, review queue |
| `analysis/report.py`, `analysis/lineage.py` | Coverage and transition SQL, charts, per-player lineage |
| `db/schema.sql` | `seasons`, `players`, `player_aliases`, `roster_entries`, `career_events` |
| `reports/` | Generated tables and figures from the current run |
