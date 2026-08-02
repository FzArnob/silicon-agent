from __future__ import annotations

import sqlite3
from typing import Any

from ..db import get_connection
from ..defaults import DEFAULT_INPUT_SET, INPUT_FIELDS, INPUT_KEYS


class InputSetError(Exception):
    """Raised for user-correctable problems (duplicate name, missing set)."""


def _field_values(payload: dict[str, Any], current: dict[str, Any] | None = None) -> list[Any]:
    """Values for every input column, in INPUT_KEYS order.

    Keys absent from the payload keep the set's current value, falling back to
    the seeded default when creating a new set.
    """
    fallback = current or DEFAULT_INPUT_SET
    values: list[Any] = []
    for field in INPUT_FIELDS:
        value = payload.get(field["key"], fallback[field["key"]])
        if field["type"] in ("int", "bool"):
            values.append(int(value or 0))
        else:
            values.append(str(value if value is not None else "").strip())

    if not values[INPUT_KEYS.index("name")]:
        raise InputSetError("Set name is required.")
    return values


def _select_all(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"SELECT id, {', '.join(INPUT_KEYS)} FROM input_sets ORDER BY id ASC"
    ).fetchall()
    return [dict(row) for row in rows]


def list_input_sets() -> list[dict[str, Any]]:
    with get_connection() as connection:
        return _select_all(connection)


def get_input_set(connection: sqlite3.Connection, set_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        f"SELECT id, {', '.join(INPUT_KEYS)} FROM input_sets WHERE id = ?",
        (set_id,),
    ).fetchone()
    return dict(row) if row else None


def default_input_set_id(connection: sqlite3.Connection) -> int | None:
    row = connection.execute("SELECT id FROM input_sets ORDER BY id ASC LIMIT 1").fetchone()
    return int(row[0]) if row else None


def create_input_set(payload: dict[str, Any]) -> dict[str, Any]:
    values = _field_values(payload)
    placeholders = ", ".join("?" for _ in INPUT_KEYS)
    with get_connection() as connection:
        try:
            cursor = connection.execute(
                f"INSERT INTO input_sets ({', '.join(INPUT_KEYS)}) VALUES ({placeholders})",
                tuple(values),
            )
        except sqlite3.IntegrityError as exc:
            raise InputSetError("An input set with that name already exists.") from exc
        created = get_input_set(connection, int(cursor.lastrowid))
    if created is None:
        raise InputSetError("Failed to create input set.")
    return created


def update_input_set(set_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    assignments = ", ".join(f"{key} = ?" for key in INPUT_KEYS)
    with get_connection() as connection:
        current = get_input_set(connection, set_id)
        if current is None:
            raise InputSetError("Input set not found.")
        values = _field_values(payload, current)
        try:
            connection.execute(
                f"UPDATE input_sets SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (*values, set_id),
            )
        except sqlite3.IntegrityError as exc:
            raise InputSetError("An input set with that name already exists.") from exc
        updated = get_input_set(connection, set_id)
    if updated is None:
        raise InputSetError("Input set not found.")
    return updated


def delete_input_set(set_id: int) -> None:
    with get_connection() as connection:
        if get_input_set(connection, set_id) is None:
            raise InputSetError("Input set not found.")
        total = connection.execute("SELECT COUNT(*) FROM input_sets").fetchone()[0]
        if total <= 1:
            raise InputSetError("At least one input set must exist.")
        connection.execute("DELETE FROM input_sets WHERE id = ?", (set_id,))
