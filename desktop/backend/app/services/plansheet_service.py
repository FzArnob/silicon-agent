from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

from ..db import get_connection
from ..defaults import ROW_COLUMNS
from ..generator import generate_plansheet_rows
from .input_set_service import default_input_set_id, get_input_set


class PlansheetError(Exception):
    """Raised for user-correctable problems (unknown input set, generation failure)."""


def _current_month() -> str:
    return date.today().strftime("%Y-%m")


def _fetch_plansheet(connection: sqlite3.Connection, month: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, input_set_id FROM plansheets WHERE month = ?", (month,)
    ).fetchone()


def _ensure_plansheet_id(connection: sqlite3.Connection, month: str, input_set_id: int) -> int:
    connection.execute(
        """
        INSERT INTO plansheets (month, input_set_id)
        VALUES (?, ?)
        ON CONFLICT(month) DO UPDATE SET
            input_set_id = excluded.input_set_id,
            updated_at = CURRENT_TIMESTAMP
        """,
        (month, input_set_id),
    )
    return int(connection.execute("SELECT id FROM plansheets WHERE month = ?", (month,)).fetchone()[0])


def _load_rows(connection: sqlite3.Connection, plansheet_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT {', '.join(ROW_COLUMNS)}
        FROM plansheet_rows
        WHERE plansheet_id = ?
        ORDER BY row_order ASC
        """,
        (plansheet_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _replace_rows(connection: sqlite3.Connection, plansheet_id: int, rows: list[dict[str, Any]]) -> None:
    connection.execute("DELETE FROM plansheet_rows WHERE plansheet_id = ?", (plansheet_id,))
    placeholders = ", ".join("?" for _ in ROW_COLUMNS)
    for index, row in enumerate(rows, start=1):
        connection.execute(
            f"""
            INSERT INTO plansheet_rows (plansheet_id, row_order, {', '.join(ROW_COLUMNS)})
            VALUES (?, ?, {placeholders})
            """,
            (plansheet_id, index, *(str(row.get(column, "") or "") for column in ROW_COLUMNS)),
        )


def _resolve_input_set_id(connection: sqlite3.Connection, requested: Any, fallback: Any = None) -> int:
    for candidate in (requested, fallback):
        if candidate is None:
            continue
        if get_input_set(connection, int(candidate)) is not None:
            return int(candidate)

    default_id = default_input_set_id(connection)
    if default_id is None:
        raise PlansheetError("No input set exists.")
    return default_id


def get_plansheet(month: str) -> dict[str, Any]:
    with get_connection() as connection:
        plansheet = _fetch_plansheet(connection, month)
        if plansheet is None:
            return {
                "exists": False,
                "month": month,
                "current_month": _current_month(),
                "input_set_id": _resolve_input_set_id(connection, None),
                "rows": [],
            }

        return {
            "exists": True,
            "month": month,
            "current_month": _current_month(),
            "input_set_id": _resolve_input_set_id(connection, plansheet["input_set_id"]),
            "rows": _load_rows(connection, int(plansheet["id"])),
        }


def save_plansheet(month: str, input_set_id: Any, rows: list[dict[str, Any]]) -> dict[str, Any]:
    with get_connection() as connection:
        resolved_id = _resolve_input_set_id(connection, input_set_id)
        plansheet_id = _ensure_plansheet_id(connection, month, resolved_id)
        _replace_rows(connection, plansheet_id, rows)
    return get_plansheet(month)


def set_plansheet_input_set(month: str, input_set_id: Any) -> dict[str, Any]:
    with get_connection() as connection:
        plansheet = _fetch_plansheet(connection, month)
        if plansheet is not None:
            resolved_id = _resolve_input_set_id(connection, input_set_id)
            connection.execute(
                "UPDATE plansheets SET input_set_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (resolved_id, int(plansheet["id"])),
            )
    return get_plansheet(month)


def delete_plansheet(month: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM plansheets WHERE month = ?", (month,))


def generate_and_save_plansheet(month: str, input_set_id: Any) -> dict[str, Any]:
    with get_connection() as connection:
        resolved_id = _resolve_input_set_id(connection, input_set_id)
        plan_input = get_input_set(connection, resolved_id)

    if plan_input is None:
        raise PlansheetError("Input set not found.")

    try:
        rows = generate_plansheet_rows(plan_input, month)
    except RuntimeError as exc:
        raise PlansheetError(str(exc)) from exc

    with get_connection() as connection:
        plansheet_id = _ensure_plansheet_id(connection, month, resolved_id)
        _replace_rows(connection, plansheet_id, rows)

    return get_plansheet(month)
