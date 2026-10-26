"""Field-level cleaning for roster records: names, class years, positions, hometowns, sizes."""

from __future__ import annotations

import re
import unicodedata

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

CLASS_CODES = {
    "fr": "FR", "freshman": "FR",
    "so": "SO", "sophomore": "SO",
    "jr": "JR", "junior": "JR",
    "sr": "SR", "senior": "SR",
    "gr": "GR", "graduate": "GR", "grad": "GR", "5th": "GR", "fifth": "GR", "6th": "GR",
}

# AP-style, postal, and full state names as they appear across roster eras.
STATE_ALIASES = {
    "AL": ["ala", "alabama"], "AK": ["alaska"], "AZ": ["ariz", "arizona"], "AR": ["ark", "arkansas"],
    "CA": ["calif", "cal", "california"], "CO": ["colo", "colorado"], "CT": ["conn", "connecticut"],
    "DE": ["del", "delaware"], "DC": ["d.c", "washington d.c"], "FL": ["fla", "florida"],
    "GA": ["ga", "georgia"], "HI": ["hawaii"], "ID": ["idaho"], "IL": ["ill", "illinois"],
    "IN": ["ind", "indiana"], "IA": ["iowa"], "KS": ["kan", "kans", "kansas"], "KY": ["ky", "kentucky"],
    "LA": ["la", "louisiana"], "ME": ["maine"], "MD": ["md", "maryland"], "MA": ["mass", "massachusetts"],
    "MI": ["mich", "michigan"], "MN": ["minn", "minnesota"], "MS": ["miss", "mississippi"],
    "MO": ["mo", "missouri"], "MT": ["mont", "montana"], "NE": ["neb", "nebr", "nebraska"],
    "NV": ["nev", "nevada"], "NH": ["n.h", "new hampshire"], "NJ": ["n.j", "new jersey"],
    "NM": ["n.m", "new mexico"], "NY": ["n.y", "new york"], "NC": ["n.c", "north carolina"],
    "ND": ["n.d", "north dakota"], "OH": ["ohio"], "OK": ["okla", "oklahoma"], "OR": ["ore", "oregon"],
    "PA": ["pa", "penn", "pennsylvania"], "RI": ["r.i", "rhode island"], "SC": ["s.c", "south carolina"],
    "SD": ["s.d", "south dakota"], "TN": ["tenn", "tennessee"], "TX": ["texas", "tex"],
    "UT": ["utah"], "VT": ["vt", "vermont"], "VA": ["va", "virginia"], "WA": ["wash", "washington"],
    "WV": ["w.va", "w.v", "west virginia"], "WI": ["wis", "wisc", "wisconsin"], "WY": ["wyo", "wyoming"],
}
def _state_key(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


STATE_LOOKUP = {code.lower(): code for code in STATE_ALIASES}
for _code, _names in STATE_ALIASES.items():
    for _name in _names:
        STATE_LOOKUP[_state_key(_name)] = _code


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def display_name(first: str | None, last: str | None) -> str:
    return re.sub(r"\s+", " ", f"{first or ''} {last or ''}").strip()


def split_suffix(last: str | None) -> tuple[str | None, str | None]:
    if not last:
        return last, None
    parts = last.replace(",", " ").split()
    if len(parts) > 1 and parts[-1].lower().rstrip(".") in SUFFIXES:
        return " ".join(parts[:-1]), parts[-1]
    return last, None


def name_key(first: str | None, last: str | None) -> str:
    """Matching key: lowercase ASCII, punctuation and suffix dropped ('A.J. Johnson Jr.' -> 'aj johnson')."""
    last, _ = split_suffix(last)
    first_key = re.sub(r"[^a-z]", "", strip_accents(first or "").lower())
    last_key = re.sub(r"[^a-z ]", "", strip_accents((last or "").replace("-", " ")).lower())
    return " ".join(t for t in (first_key, " ".join(last_key.split())) if t)


def parse_class(raw: str | None) -> tuple[str | None, int]:
    """'R-So.' -> ('SO', 1); 'Gr.' -> ('GR', 0). Unknown labels return (None, redshirt flag)."""
    if not raw:
        return None, 0
    text = raw.strip().lower().replace(".", "")
    redshirt = 0
    match = re.match(r"^(r-|rs-?|r |redshirt )\s*(.*)$", text)
    if match:
        redshirt, text = 1, match.group(2)
    if text in ("r", "rs", "redshirt"):
        return "RS", 1
    return CLASS_CODES.get(text.strip()), redshirt


def clean_position(raw: str | None) -> str | None:
    if not raw:
        return None
    return re.sub(r"[^A-Z/]", "", raw.upper()) or None


def parse_jersey(raw) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip().lstrip("#")
    if text.isdigit() and 0 <= int(text) <= 99:
        return int(text)
    return None


def height_inches(feet, inches) -> int | None:
    try:
        total = int(feet) * 12 + int(inches or 0)
    except (TypeError, ValueError):
        return None
    return total if 60 <= total <= 90 else None


def parse_weight(raw) -> int | None:
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        return None
    return value if 140 <= value <= 450 else None


def parse_hometown(raw: str | None) -> tuple[str | None, str | None]:
    """'Antioch, Calif.' -> ('Antioch', 'CA'). A bare city keeps state None.

    Some 2012 rows leak the high school into the field: 'Rock Hill, S.C. (Northwestern'.
    """
    if not raw:
        return None, None
    text = re.sub(r"\s+", " ", raw).strip()
    if "," not in text:
        return text, None
    city, _, state = text.rpartition(",")
    state_only = re.sub(r"\(.*$", "", state).strip()
    code = STATE_LOOKUP.get(_state_key(state_only))
    if code is None:
        # Foreign hometowns ('Sydney, Australia') keep the region text as-is.
        return city.strip(), state.strip()
    return city.strip(), code
