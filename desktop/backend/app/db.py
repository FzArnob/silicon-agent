from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "app.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS plansheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plansheet_inputs (
    plansheet_id INTEGER PRIMARY KEY,
    month TEXT NOT NULL,
    raw_input_json TEXT NOT NULL,
    channel_name TEXT,
    category TEXT,
    sub_category_name TEXT,
    series_name TEXT,
    content_type TEXT,
    posts_per_week INTEGER,
    is_series INTEGER,
    goal TEXT,
    tone TEXT,
    duration_range_seconds TEXT,
    language TEXT,
    timezone TEXT,
    storage_path TEXT,
    special_instructions TEXT,
    target_audience_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plansheet_id) REFERENCES plansheets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plansheet_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plansheet_id INTEGER NOT NULL,
    row_order INTEGER NOT NULL,
    post_id TEXT NOT NULL,
    upload_date TEXT,
    upload_time TEXT,
    title TEXT,
    description TEXT,
    hashtags TEXT,
    keywords TEXT,
    category TEXT,
    sub_category_name TEXT,
    series_name TEXT,
    episode_number INTEGER,
    landscape_video_path TEXT,
    landscape_thumbnail_path TEXT,
    portrait_video_path TEXT,
    portrait_thumbnail_path TEXT,
    ai_flag TEXT,
    kids_flag TEXT,
    status TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plansheet_id) REFERENCES plansheets(id) ON DELETE CASCADE,
    UNIQUE (plansheet_id, row_order)
);

CREATE INDEX IF NOT EXISTS idx_plansheet_rows_sheet_order
    ON plansheet_rows (plansheet_id, row_order);
"""


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(SCHEMA_SQL)
        connection.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    init_db()
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


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)
