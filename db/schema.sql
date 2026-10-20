-- VolLineage relational schema
-- Identity (players) is separate from a season appearance (roster_entries)
-- and from the strings used to match drifting names and numbers (player_aliases).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS seasons (
    season_year INTEGER PRIMARY KEY, -- fall of the season, e.g. 1998
    label TEXT NOT NULL,             -- display label, e.g. '1998'
    conference TEXT,
    head_coach TEXT,
    notes TEXT,
    CHECK (season_year BETWEEN 1998 AND 2100)
);

CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    suffix TEXT,
    hometown TEXT,
    home_state TEXT,
    high_school TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Evidence that a source string refers to a player. Low-confidence rows stay
-- here so a bad merge can be reversed without rewriting roster history.
CREATE TABLE IF NOT EXISTS player_aliases (
    alias_id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players (player_id) ON DELETE CASCADE,
    alias_text TEXT NOT NULL,
    alias_type TEXT NOT NULL CHECK (
        alias_type IN ('name', 'jersey', 'source_id', 'other')
    ),
    season_year INTEGER REFERENCES seasons (season_year),
    source_name TEXT,
    confidence REAL,
    notes TEXT,
    CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0))
);

CREATE TABLE IF NOT EXISTS roster_entries (
    roster_entry_id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    season_year INTEGER NOT NULL REFERENCES seasons (season_year),
    jersey_number INTEGER,
    position TEXT,
    class_year TEXT CHECK (
        class_year IS NULL OR class_year IN ('FR', 'SO', 'JR', 'SR', 'GR', 'RS')
    ),
    redshirt INTEGER NOT NULL DEFAULT 0 CHECK (redshirt IN (0, 1)),
    height_inches INTEGER,
    weight_lbs INTEGER,
    games_played INTEGER,
    games_started INTEGER,
    status TEXT NOT NULL DEFAULT 'active' CHECK (
        status IN (
            'active',
            'redshirt',
            'medical',
            'transfer_in',
            'transfer_out',
            'other'
        )
    ),
    source_name TEXT NOT NULL,
    source_url TEXT,
    snapshot_timestamp TEXT,
    raw_name TEXT NOT NULL,
    ingested_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (jersey_number IS NULL OR jersey_number BETWEEN 0 AND 99),
    CHECK (height_inches IS NULL OR height_inches BETWEEN 60 AND 90),
    CHECK (weight_lbs IS NULL OR weight_lbs BETWEEN 140 AND 450),
    UNIQUE (player_id, season_year, source_name)
);

-- Derived transitions: number changes, position switches, redshirts, portal moves.
-- from_value / to_value hold the previous and next jersey, position, or school.
CREATE TABLE IF NOT EXISTS career_events (
    event_id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    season_year INTEGER REFERENCES seasons (season_year),
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'roster_join',
            'roster_exit',
            'position_change',
            'jersey_change',
            'redshirt',
            'transfer_in',
            'transfer_out',
            'medical',
            'other'
        )
    ),
    event_date TEXT,
    from_value TEXT,
    to_value TEXT,
    counterparty_school TEXT,
    notes TEXT,
    source_name TEXT,
    source_url TEXT
);

-- IFNULL keeps a season-independent alias from being inserted twice.
-- SQLite UNIQUE allows multiple NULLs in season_year.
CREATE UNIQUE INDEX IF NOT EXISTS idx_aliases_identity
    ON player_aliases (player_id, alias_type, alias_text, IFNULL(season_year, -1));
CREATE INDEX IF NOT EXISTS idx_aliases_player ON player_aliases (player_id);
CREATE INDEX IF NOT EXISTS idx_aliases_text ON player_aliases (alias_type, alias_text);
CREATE INDEX IF NOT EXISTS idx_roster_season ON roster_entries (season_year);
CREATE INDEX IF NOT EXISTS idx_roster_player ON roster_entries (player_id);
CREATE INDEX IF NOT EXISTS idx_roster_jersey ON roster_entries (season_year, jersey_number);
CREATE INDEX IF NOT EXISTS idx_events_player ON career_events (player_id, season_year);
