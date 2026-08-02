from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .defaults import DEFAULT_INPUT_SET, INPUT_KEYS

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "app.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS input_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    channel_name TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    sub_category_name TEXT NOT NULL DEFAULT '',
    is_series INTEGER NOT NULL DEFAULT 0,
    series_name TEXT NOT NULL DEFAULT '',
    content_type TEXT NOT NULL DEFAULT '',
    target_audience TEXT NOT NULL DEFAULT '',
    posts_per_week INTEGER NOT NULL DEFAULT 7,
    goal TEXT NOT NULL DEFAULT '',
    tone TEXT NOT NULL DEFAULT '',
    duration_range_seconds TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT '',
    timezone TEXT NOT NULL DEFAULT '',
    storage_path TEXT NOT NULL DEFAULT '',
    special_instructions TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plansheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL UNIQUE,
    input_set_id INTEGER REFERENCES input_sets(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plansheet_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plansheet_id INTEGER NOT NULL REFERENCES plansheets(id) ON DELETE CASCADE,
    row_order INTEGER NOT NULL,
    post_id TEXT NOT NULL DEFAULT '',
    date_time TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    hashtags TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    sub_category_name TEXT NOT NULL DEFAULT '',
    series_name TEXT NOT NULL DEFAULT '',
    episode_number TEXT NOT NULL DEFAULT '',
    landscape_video_path TEXT NOT NULL DEFAULT '',
    landscape_thumbnail_path TEXT NOT NULL DEFAULT '',
    portrait_video_path TEXT NOT NULL DEFAULT '',
    portrait_thumbnail_path TEXT NOT NULL DEFAULT '',
    ai_flag TEXT NOT NULL DEFAULT '',
    kids_flag TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (plansheet_id, row_order)
);

CREATE INDEX IF NOT EXISTS idx_plansheet_rows_sheet_order
    ON plansheet_rows (plansheet_id, row_order);
"""


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        _migrate_legacy_tables(connection)
        connection.executescript(SCHEMA_SQL)
        _seed_default_input_set(connection)
        connection.commit()
    finally:
        connection.close()


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _migrate_legacy_tables(connection: sqlite3.Connection) -> None:
    """Bring a pre-input-sets database up to the current schema, keeping rows."""
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }

    # Per-month generation input is replaced by reusable named input sets.
    connection.execute("DROP TABLE IF EXISTS plansheet_inputs")

    if "plansheets" in tables and "input_set_id" not in _table_columns(connection, "plansheets"):
        connection.execute("ALTER TABLE plansheets ADD COLUMN input_set_id INTEGER")

    if "plansheet_rows" not in tables:
        return

    row_columns = _table_columns(connection, "plansheet_rows")
    if "upload_date" not in row_columns:
        return

    # Legacy split date/time columns: fold them into date_time, then rebuild the
    # table with only the current columns.
    if "date_time" not in row_columns:
        connection.execute("ALTER TABLE plansheet_rows ADD COLUMN date_time TEXT")
    connection.execute(
        """
        UPDATE plansheet_rows
        SET date_time = TRIM(COALESCE(upload_date, '')) || ' ' || TRIM(COALESCE(upload_time, ''))
        WHERE TRIM(COALESCE(date_time, '')) = ''
          AND TRIM(COALESCE(upload_date, '')) <> ''
        """
    )
    connection.execute("ALTER TABLE plansheet_rows RENAME TO plansheet_rows_legacy")
    connection.executescript(SCHEMA_SQL)
    connection.execute(
        """
        INSERT INTO plansheet_rows (
            id, plansheet_id, row_order, post_id, date_time, title, description,
            hashtags, keywords, category, sub_category_name, series_name,
            episode_number, landscape_video_path, landscape_thumbnail_path,
            portrait_video_path, portrait_thumbnail_path, ai_flag, kids_flag,
            status, created_at, updated_at
        )
        SELECT
            id, plansheet_id, row_order,
            COALESCE(post_id, ''), COALESCE(date_time, ''), COALESCE(title, ''),
            COALESCE(description, ''), COALESCE(hashtags, ''), COALESCE(keywords, ''),
            COALESCE(category, ''), COALESCE(sub_category_name, ''),
            COALESCE(series_name, ''), COALESCE(episode_number, ''),
            COALESCE(landscape_video_path, ''), COALESCE(landscape_thumbnail_path, ''),
            COALESCE(portrait_video_path, ''), COALESCE(portrait_thumbnail_path, ''),
            COALESCE(ai_flag, ''), COALESCE(kids_flag, ''), COALESCE(status, ''),
            created_at, updated_at
        FROM plansheet_rows_legacy
        """
    )
    connection.execute("DROP TABLE plansheet_rows_legacy")


def _seed_default_input_set(connection: sqlite3.Connection) -> None:
    count = connection.execute("SELECT COUNT(*) FROM input_sets").fetchone()[0]
    if count:
        return

    placeholders = ", ".join("?" for _ in INPUT_KEYS)
    connection.execute(
        f"INSERT INTO input_sets ({', '.join(INPUT_KEYS)}) VALUES ({placeholders})",
        tuple(DEFAULT_INPUT_SET[key] for key in INPUT_KEYS),
    )


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
