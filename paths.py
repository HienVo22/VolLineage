"""Filesystem locations shared by the scrapers, pipeline, and analysis."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
CFBD_DIR = RAW / "cfbd"
CDX_DIR = RAW / "cdx"
HTML_DIR = RAW / "html"
MANIFEST = RAW / "manifest.jsonl"
SEASON_CAPTURES = CDX_DIR / "season_captures.json"
ERA_INVENTORY = CDX_DIR / "era_inventory.json"

PROCESSED = ROOT / "data" / "processed"
ROSTER_RAW = PROCESSED / "roster_raw.csv"
ROSTER_CLEAN = PROCESSED / "roster_clean.csv"
REVIEW_QUEUE = PROCESSED / "review_queue.csv"
PORTAL_CSV = PROCESSED / "cfbd_portal_tennessee.csv"

SCHEMA = ROOT / "db" / "schema.sql"
DB = ROOT / "db" / "vollineage.sqlite3"

REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
PORTAL_COMPARE = REPORTS / "portal_vs_proxy.csv"
PORTAL_FIGURE = FIGURES / "portal_vs_proxy.png"
