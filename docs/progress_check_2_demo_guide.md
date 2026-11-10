# VolLineage: Progress Check 2 demo guide

**Length:** under 5 minutes, live, for the professor or TA.
**Who talks:** Hamzah shows the download. Bansari shows the chart, the gap, and what is left for December 1.

This is the last check before the final report. It is not the final product. Practice the script once out loud before class.

---

## 1. What the project is

VolLineage rebuilds every Tennessee football roster from 1998 to 2025 from old copies of UT's athletics site, then follows players across seasons to measure roster change: who returns, who arrives from another school, and how that differs by head coach.

Progress Check 1 already did the roster archive: the pages are downloaded, parsed, and stored in a database. Do not spend the check re-explaining that pipeline. One sentence is enough.

## 2. What this check covers

The assignment asks for four things. This is the new piece since Progress Check 1:

| Show this | What it is |
| --- | --- |
| Current status | The 1998–2025 rosters from Progress Check 1 are still the base. The new work is a second source: the NCAA transfer-portal list. |
| Meaningful progress | A live request to the CollegeFootballData API, the Tennessee rows it returns for 2021–2025, and one chart. |
| A problem | The portal list and the roster's "previous school" field do not count the same thing, and the names are not linked yet. |
| Next | Match portal names to roster players, then compare Tennessee with other FBS schools in the final report. |

What we are **not** claiming yet:

- A finished transfer count
- That each portal name is the same person as a roster row
- How Tennessee compares with the rest of the FBS
- The final charts or the written report

Say this line if the check starts to sound finished:

> "Progress Check 1 counted a previous school on the roster page. We now have the portal list itself for Tennessee since 2021. The two counts do not match, and linking each portal name to a roster row is the work left before December 1."

## 3. What the new data is

CollegeFootballData.com publishes a transfer-portal list for each season. The list is every school, not just Tennessee. Our script downloads 2021 through 2025 and keeps a row only when Tennessee is the school the player left or the school the player chose.

| Column | Meaning |
| --- | --- |
| `direction = in` | The portal list says the destination is Tennessee. `other_school` is the school they left. |
| `direction = out` | The portal list says the origin is Tennessee. `other_school` is the destination, when one is listed. |
| `eligibility = Withdrawn` | The player left the portal. These rows stay in the CSV. They are **not** included in the chart. |

The roster count from Progress Check 1 is different. It counts a player whose **first Tennessee roster** lists any previous school, including junior college. It is not a portal entry.

The chart puts those two counts side by side for the same seasons. It does not decide which players are the same person.

## 4. Setup before class

Do this on the laptop you will use in class. The roster database from Progress Check 1 has to exist first.

```bash
git pull
cd VolLineage
source .venv/bin/activate
```

If this laptop has never built the roster database:

```bash
make setup
make pipeline
```

Then add a free CollegeFootballData key. Create an account at [collegefootballdata.com](https://collegefootballdata.com), copy `.env.example` to `.env` if you do not already have one, and set:

```bash
CFBD_API_KEY=your-key-here
```

Do not commit `.env`. Then download the portal list and build the chart:

```bash
make portal
```

That takes well under a minute. It writes:

- `data/raw/cfbd/portal_2021.json` through `portal_2025.json` (raw API responses, not in git)
- `data/processed/cfbd_portal_tennessee.csv` (Tennessee rows only, not in git)
- `reports/portal_vs_proxy.csv`
- `reports/figures/portal_vs_proxy.png`

Open the PNG before class so you can switch to it quickly. Make the terminal font large.

**If the Wi-Fi fails in class:** skip the live download. If `make portal` already succeeded on this laptop, run `python -m analysis.portal_compare` and show the saved chart. The raw JSON is cached, so that command does not need the network.

**If `CFBD_API_KEY` was never set:** the download stops with a 401 or a message that the key is missing. Fix the key before class. There is no offline substitute for the first download.

## 5. The five-minute script

### 1) Status (about 45 seconds, Hamzah)

> "VolLineage is a roster archive for Tennessee football from 1998 through 2025, built from archived copies of the athletics site. Progress Check 1 downloaded and parsed those rosters. Since then we added a second source: the transfer-portal list from CollegeFootballData, for Tennessee only, 2021 through 2025. We have not matched those names to our roster players yet."

### 2) Progress (about 2 minutes, Hamzah, then Bansari)

**Live request (Hamzah).** This re-downloads one season. The other seasons stay in the saved files.

```bash
python -m scrapers.cfbd --years 2024 --force
```

Point at the line that says `2024: downloaded ... portal rows`. Then point at the count line:

```text
  2024  in  ..  out  ..  withdrawn  ..
```

> "The API returns the whole country's portal for that season. We keep only the rows where Tennessee is the origin or the destination. 'In' means the list says they chose Tennessee. 'Out' means the list says they left Tennessee. 'Withdrawn' means they took their name back out of the portal, so we do not count those in the chart."

Show five rows so the format is visible:

```bash
python -c "import pandas as pd; df=pd.read_csv('data/processed/cfbd_portal_tennessee.csv'); print(df[df.season_year==2024][['season_year','direction','player_name','other_school','eligibility']].head().to_string(index=False))"
```

**Chart (Bansari).**

```bash
python -m analysis.portal_compare
```

Then open `reports/figures/portal_vs_proxy.png`.

How to read it:

- Each pair of bars is one season.
- The blue bar is the Progress Check 1 count: players whose first Tennessee roster lists a previous school.
- The orange bar is the new count: portal entries whose destination is Tennessee, excluding withdrawals.
- The printed table also has `portal_departures`, players whose origin is Tennessee. The chart does not show departures, so mention that column if you are asked.

> "These bars are not supposed to match. The blue bar includes junior-college players and anyone else who listed a previous school. The orange bar is only the portal list, and a portal entry is not the same thing as actually appearing on the next roster. We have not linked the names, so this is a comparison of two lists, not a finished transfer total."

### 3) Problems (about 45 seconds, Bansari)

1. **The portal list is not an enrollment list.** A destination can be empty, and some entries are withdrawn or still pending.
2. **The names are not linked** to the roster database, so we cannot yet say which portal row is which VolLineage player.
3. **The portal source starts in 2021.** Seasons before that still use the roster field only.
4. **The download needs a free API key** and a network connection. The raw responses are cached after the first successful run.

### 4) Next, before December 1 (about 30 seconds, Bansari)

> "Next we match portal names to roster players and check a sample by hand. Then we add other FBS schools so Tennessee is not only compared with itself. The older roster seasons, the position labels, and the written report are still ahead of us. This check is the second source, not the final analysis."

## 6. If they ask something else

**"Is this the final transfer finding?"** No. Say the two lists are still separate.

**"Why is the blue bar higher or lower?"** Blue counts a previous school on the first Tennessee roster, including junior college. Orange counts a portal destination of Tennessee. They overlap, but they are not the same set of people.

**"Can you show one player from Progress Check 1?"** Only if there is time. `python -m analysis.lineage "Jauan Jennings"` is the old roster history. It does not include the portal list.

**"Where is the code?"** `scrapers/cfbd.py` downloads the portal. `analysis/portal_compare.py` makes the table and the chart. Neither file writes portal rows into the player tables.
