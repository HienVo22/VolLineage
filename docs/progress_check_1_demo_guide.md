# VolLineage: Progress Check 1 demo guide

**Presenters:** Hamzah and Bansari (Hien is not presenting this time).
**Length:** about 5 minutes, live, for the professor or TA during class.

Suggested reading order: sections 1–3 to understand the project, section 4 to set up your laptop, then practice section 7 out loud at least once together.

---

## 1. What the project is about

**In one sentence:** VolLineage rebuilds every Tennessee football roster from 1998 to today using old saved copies of UT's athletics website, then follows each player across seasons to measure how the roster changes over time.

**The problem.** UT's athletics site (utsports.com) only shows the current roster. Old rosters were overwritten each year, and the site has been rebuilt several times since 1998. The only surviving copies are in the **Internet Archive's Wayback Machine**, which saved snapshots of the site over the years. Those copies are messy:

- Different years use different page layouts.
- Some years were saved several times, and the copies don't always agree.
- The same player can show up with a different jersey number, position, class label ("R-So."), or name spelling from one year to the next, and there is no reliable ID that ties his seasons together.

That's why this is a **digital archaeology** project: we're recovering a record that the original website no longer keeps, and we keep track of exactly where every piece of data came from.

**The questions we want to answer for the final report:**

- How much of the roster returns from one year to the next (**retention**)?
- Did the **transfer portal** (opened in 2018) change how many players arrive from other schools?
- How often do players switch **positions** or **jersey numbers**?
- How do these numbers differ between head coaches (Fulmer, Kiffin, Dooley, Jones, Pruitt, Heupel)?

**Who owns what (from the proposal):**

| Person | Workstream |
| --- | --- |
| Hamzah | Getting the data: finding and downloading archived pages, parsing them |
| Hien | Cleaning the data, linking each player's seasons together, the database |
| Bansari | Analysis, charts, the written report and presentation |

---

## 2. What Progress Check 1 is and what we'll show

The assignment is a short live demo proving we've **moved past planning and are actually working with data**. The project does not need to be finished, and the results do not need to be polished. Every team member should understand the current state of the project and be ready for questions.

The assignment asks for five things. This is what we'll show for each:

| The assignment asks for | What we show | Who |
| --- | --- | --- |
| **1. Project status:** goal, what's done, what's in progress | Two-sentence summary of the project, then the done and in-progress lists | Hamzah |
| **2. Data collected:** source, how we got it, how much, format | Wayback Machine, 87 saved pages, all 28 seasons, 3,020 player rows; one download record and five sample rows | Hamzah |
| **3. Live evidence of progress** | A live download from the Wayback Machine, one database query, one early chart | Hamzah, then Bansari |
| **4. Problems or risks** | Five short points | Bansari |
| **5. Next steps** | What we do before the final report | Bansari |

Some extras are already built (player matching, more charts). **Don't show them unless asked.** Section 8 has them ready if a question comes up.

---

## 3. How it works, in plain language

### The steps

```
1. Find the pages     ->  2. Download     ->  3. Pull out players  ->  4. Clean      ->  5. Database  ->  6. Charts
   (Wayback index)        (saved HTML)        (one row per player)     (fix labels)      (SQLite)         (reports/)
```

1. **Find the pages.** UT's current site has one roster page per season: `utsports.com/sports/football/roster/1998`, `/1999`, and so on through `/2025`. We ask the Wayback Machine which saved copies of each page exist. Every season has 1 to 5 copies.
2. **Download.** We download every copy (87 pages, 77 MB) and save it to our laptop, so we never have to download it again. Every download is logged with its URL and date in `data/raw/manifest.jsonl`.
3. **Pull out the players.** Each page has the full roster hidden inside the page's code as structured data (JSON). We extract it into one row per player: name, jersey, position, class, height, weight, hometown, high school, and previous school.
4. **Clean.** We make labels consistent. For example, "R-So." becomes class "SO" plus a redshirt flag, and "Tenn.", "Tennessee", and "T.N." all become "TN".
5. **Database.** Everything goes into one SQLite file (`db/vollineage.sqlite3`). Every row remembers which saved copy it came from.
6. **Charts and tables.** Simple counts and charts go to the `reports/` folder.

### Words you might hear or need to use

| Term | What it means |
| --- | --- |
| **Wayback Machine** | The Internet Archive's service that has saved copies of websites since the 1990s (web.archive.org). |
| **Capture / snapshot / copy** | One saved copy of a web page on a specific date and time, for example the 2024 roster page as saved on Dec 14, 2024. |
| **CDX API** | The Wayback Machine's index. You give it a URL and it lists every saved copy with its date. |
| **Sidearm** | The company that runs UT's athletics website (and many other schools' sites). |
| **Manifest** | Our log file with one line per downloaded page: where it came from, when it was saved, and whether we could read it. |
| **Provenance** | A record of where each piece of data came from. Every row in our database has its source URL and capture date. |
| **CSV / SQLite** | A CSV is a spreadsheet-style text file. SQLite is a small database stored in one file, which we query with SQL. |
| **Entity resolution** | Deciding when two rows are the same real person, such as "A.J. Johnson" in 2011 and "AJ Johnson" in 2013. |
| **Redshirt** | A player who sits out a season without using a year of eligibility. Rosters mark it with "R-" (for example "R-Fr."). |
| **Transfer portal** | The NCAA system, opened in October 2018, that lets players list themselves to transfer schools. |

---

## 4. Setup and dependencies

Do this once on each laptop that will run the demo. **Do it tonight, not in class.** The first build downloads about 77 MB and takes 3–4 minutes.

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

If you already cloned the repo, run `git pull` instead of `git clone`.

Without `make`, run the equivalent by hand:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Build the data (required before the demo)

The downloaded pages, CSVs, and database are **not** stored in git, so each laptop has to build them once:

```bash
make pipeline                # find -> download -> extract -> clean -> database -> charts (about 3-4 minutes)
make test                    # should end with: 28 passed
```

When `make pipeline` finishes, the last lines should mention `reports/figures/...png`. If anything fails, message Hien before class.

**Every command in this guide runs from the repository folder, after `source .venv/bin/activate`.** If you see `ModuleNotFoundError` or `command not found: python`, you forgot to activate the virtual environment or you're in the wrong folder.

---

## 5. Numbers to know

Memorize the bold ones; they answer most "how much data?" questions.

| What | Value |
| --- | --- |
| Source | Wayback Machine copies of `utsports.com/sports/football/roster/YYYY` |
| Seasons covered | **all 28** (1998–2025) |
| Saved pages downloaded | **87** (77 MB of HTML). 79 are readable; 8 are from UT's new late-2025 website, which doesn't include the roster data. |
| Player rows | **8,610** from all 87 pages; **3,020** after keeping one copy per season |
| Distinct players | about **1,146** (early estimate; matching is still in progress) |
| Format | Saved HTML pages, then CSV files (`data/processed/`), then a SQLite database (`db/vollineage.sqlite3`) |
| Football pages saved across all of UT's old website versions | about **46,000** (the proposal said 49,177; see Risks) |

---

## 6. Before class

1. Both of you finish section 4 so `make pipeline` and `make test` work. **Decide whose laptop you'll use.** One laptop is simpler; Hamzah can type while Bansari talks.
2. Open a terminal in the repo folder, run `source .venv/bin/activate`, and make the font large (Cmd and + a few times).
3. Open `reports/figures/arrivals_by_season.png` in Preview so you can switch to it quickly.
4. Check the Wi-Fi: `curl -sI https://web.archive.org | head -1` should print `HTTP/2 200`.
5. Optional: put the commands from section 7 in a text file so you can copy and paste instead of typing.

**If the Wi-Fi or the Wayback Machine is down:** skip the live download in part 3. Everything else works offline because the pages are already saved. Say: "The download script saves every page locally, so we can rebuild without the internet," then run `make extract clean load` instead.

---

## 7. The five-minute script

Quoted text is a suggestion; say it in your own words. The timing is a guide.

### Part 1: Project status (0:00–0:45, Hamzah)

> "Our project, VolLineage, rebuilds every Tennessee football roster from 1998 to today using old copies of UT's athletics site saved by the Internet Archive. Then we follow each player across seasons to measure how the roster changes: how many players return each year, how many transfer in, and how that differs by head coach.
>
> **So far** we've found the archived roster pages, written a script that downloads them, and turned every season into a spreadsheet and a database.
> **In progress:** linking each player's seasons together, since names and numbers change, and cleaning up inconsistencies between years."

### Part 2: Data collected (0:45–1:45, Hamzah)

Say where the data comes from and how we got it:

> "Our **source** is the Wayback Machine. UT's site has one roster page per season, and the Wayback Machine saved 1 to 5 copies of each. We used its index to find all of them and downloaded all **87 copies, 77 MB of HTML, covering all 28 seasons**."

Show the **format**: one line of our download log.

```bash
head -n 2 data/raw/manifest.jsonl | tail -n 1 | python -m json.tool
```

What to point at in the output:

- `original_url`: the UT page this copy is of (the 1998 roster).
- `timestamp`: when the Wayback Machine saved it (`20250121...` means Jan 21, 2025).
- `parse_status: "ok"` and `players: 82`: we could read it, and it lists 82 players.

> "Every download is logged like this, so we can always trace a row back to the exact saved page it came from."

Show **how much** data there is, and what a row looks like:

```bash
wc -l data/processed/roster_raw.csv data/processed/roster_clean.csv
sqlite3 -box db/vollineage.sqlite3 "SELECT season_year, raw_name, jersey_number AS jersey, position, class_year, redshirt, height_inches, weight_lbs, snapshot_timestamp FROM roster_entries WHERE season_year = 2024 LIMIT 5;"
```

The first command shows `8611` and `3023` lines; each count includes one header line, and the last line is the total. Say:

> "That's 8,610 player rows from all the copies, and about 3,000 once we keep one copy per season. Here are five 2024 players: jersey, position, class, redshirt flag, height in inches, weight, and the date of the copy the row came from."

### Part 3: Live evidence (1:45–3:15, Hamzah, then Bansari)

**Live download (Hamzah, about 10 seconds):**

```bash
python -m scrapers.discover --start 2024 --end 2024
python -m scrapers.fetch_rosters --seasons 2024 --force
```

The first command asks the Wayback Machine which copies of the 2024 roster page exist (it finds 3). The second downloads them, newest first. Expected output:

```
2024 20250807211446  fetched  no_roster_json     0 players    2383 KB
2024 20241214044724  fetched  ok               123 players     928 KB
```

> "That's a live request to the Wayback Machine. The newest copy is from August 2025, after UT moved to a new website, and that version doesn't contain the roster data, so it reads 0 players. Our script notices and falls back to the December 2024 copy, which has all 123 players."

If the numbers or dates differ slightly, that's fine; the Wayback Machine may have saved a new copy.

**Run a query (Bansari):**

```bash
sqlite3 -box db/vollineage.sqlite3 "SELECT season_year, COUNT(*) AS players, SUM(status = 'transfer_in') AS arrived_from_another_school FROM roster_entries WHERE season_year >= 2016 GROUP BY 1;"
```

> "This is a SQL query on our database: roster size per season, and how many players arrived from another school. You can see the jump in 2021: 18, compared with 1 to 8 before 2018."

**Show the early chart (Bansari):** switch to `arrivals_by_season.png`.

How to read it: each bar is the number of players appearing on a Tennessee roster for the first time that season. The **orange** part is players who listed a previous school (transfers or junior-college players). The dashed line marks when the transfer portal opened in October 2018.

> "This is a first look, not a finding yet. The orange part grows after the portal opened and peaks in 2021, the first year players could transfer once without sitting out. We still need to check this against real transfer-portal data."

### Part 4: Problems and risks (3:15–4:15, Bansari)

1. **The website's own player IDs aren't reliable.** When UT's site added old seasons, it gave players new IDs, so the same player can have two IDs (for example, Jauan Jennings has one for 2015–16 and another for 2018–19). We have to link players ourselves using name, hometown, and high school.
2. **Copies of the same page disagree.** In 4 seasons, different saved copies list different players. For example, the July 2022 copy of the 2022 roster lists 124 players and later copies list 117. We keep every copy and pick one per season with a fixed rule.
3. **Older rosters are thinner.** Rosters before 2009 list about 90–100 players, compared with about 120 now, and seasons before 2005 have no redshirt labels. So the early years are probably incomplete.
4. **UT launched a new website in late 2025** that doesn't include the roster data the same way, so 2026 will need a new parser.
5. **Correction to our proposal.** We estimated about 49,000 saved pages, but one of our counts accidentally included every sport. For football alone it's about 46,000. This doesn't change the plan.

### Part 5: Next steps (4:15–5:00, Bansari)

> "Next, we'll finish linking players across seasons and check a sample of the matches by hand. We'll add transfer-portal data and other FBS schools' rosters from the CollegeFootballData API, so we can compare Tennessee with everyone else. We'll also read one older version of UT's site to double-check the early seasons. Then the retention and transfer analysis by coach, and the final report and presentation."

---

## 8. Backup: only if asked

These are already built. Show them only if the professor or TA asks.

**"How do you know two rows are the same player?"**

```bash
python -m analysis.lineage "Jauan Jennings"
```

This prints every season he appears in, his jersey, position, and class each year, and the two website IDs we linked. Explain the rule: we only link two IDs automatically when the name matches exactly, the hometown or high school matches, nothing contradicts, they're never on the same roster in the same year, and the career fits in six seasons. That turns 1,199 website IDs into 1,146 players. Unsure cases go to `data/processed/review_queue.csv` for a person to check rather than being merged automatically. Many come from typos in the original pages, such as "Nasvhille" and "Eerie" for Erie.

**"What cleaning have you done?"** Run `python -m pipeline.clean`. Its output lists what it fixed: 9 different class labels become 5 standard ones plus a redshirt flag, and many spellings of state names become 2-letter codes. Odd rows are flagged, not deleted.

**"Any other analysis?"** Open `reports/figures/retention_by_season.png`. About 60–70% of the roster returns each year in every coaching era so far. `python -m analysis.report | head -40` prints the tables.

**"How much exists across all of UT's old website versions?"** Run `python -m scrapers.discover --inventory`. It takes about 7 seconds and lists about 46,000 saved football pages across 4 website versions.

**"How do you know which season a page is for?"** The year is in the page address (`/roster/2013`). The script also reads the season written inside the page and rejects the copy if the two disagree.

**"How do you count a transfer?"** For now, a player whose first roster lists a previous school. That includes junior-college players, so it's an overestimate until we add the real portal data.

**"Do you share the downloaded pages?"** No. They stay on our laptops and are not in the repo; only our code and summary tables are.

**"Can I see the code?"** Briefly: `scrapers/` finds, downloads, and reads pages; `pipeline/` cleans the data and builds the database; `analysis/` holds the queries and charts. The full code walk-through belongs to Hien; you can say he owns the matching and database part.

---

## 9. Instructions for the TA or professor

Requirements and installation are in section 4. In short:

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
