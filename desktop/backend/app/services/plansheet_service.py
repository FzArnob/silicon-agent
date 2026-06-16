from __future__ import annotations

import copy
import json
from datetime import date
from typing import Any

from ..db import get_connection, row_to_dict
from ..defaults import DEFAULT_PLAN_INPUT, REQUIRED_COLUMNS, make_default_plan_input
from ..generator import generate_plansheet_rows


def _current_month() -> str:
    return date.today().strftime("%Y-%m")


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def normalize_input_payload(month: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    normalized = make_default_plan_input(month)
    if payload:
        normalized.update(copy.deepcopy(payload))

    normalized["month"] = month

    target_audience = normalized.get("target_audience", [])
    if isinstance(target_audience, str):
        target_audience = [item.strip() for item in target_audience.split(",") if item.strip()]
    elif not isinstance(target_audience, list):
        target_audience = []
    normalized["target_audience"] = [str(item) for item in target_audience if str(item).strip()]

    normalized["posts_per_week"] = int(normalized.get("posts_per_week") or 0) or 7
    normalized["is_series"] = _coerce_bool(normalized.get("is_series"))

    return normalized


def _parse_input_row(row: dict[str, Any] | None, month: str) -> dict[str, Any]:
    if row is None:
        return make_default_plan_input(month)

    data = json.loads(row["raw_input_json"])
    data["target_audience"] = json.loads(row["target_audience_json"]) if row["target_audience_json"] else data.get("target_audience", [])
    data["posts_per_week"] = row["posts_per_week"] if row["posts_per_week"] is not None else data.get("posts_per_week", 7)
    data["is_series"] = bool(row["is_series"]) if row["is_series"] is not None else data.get("is_series", False)
    data["month"] = month
    return data


def _fetch_plansheet_id(connection, month: str) -> int | None:
    row = connection.execute("SELECT id FROM plansheets WHERE month = ?", (month,)).fetchone()
    if row is None:
        return None
    return int(row[0])


def _ensure_plansheet_id(connection, month: str) -> int:
    connection.execute(
        """
        INSERT INTO plansheets (month)
        VALUES (?)
        ON CONFLICT(month) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
        """,
        (month,),
    )
    row = connection.execute("SELECT id FROM plansheets WHERE month = ?", (month,)).fetchone()
    if row is None:
        raise RuntimeError("Failed to create plansheet record")
    return int(row[0])


def _load_rows(connection, plansheet_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT *
        FROM plansheet_rows
        WHERE plansheet_id = ?
        ORDER BY row_order ASC, id ASC
        """,
        (plansheet_id,),
    ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_dict(row) or {}
        for column in REQUIRED_COLUMNS:
            value = item.get(column, "")
            item[column] = "" if value is None else str(value)
        item["episode_number"] = item.get("episode_number", "")
        result.append(item)
    return result


def _load_input(connection, plansheet_id: int, month: str) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT *
        FROM plansheet_inputs
        WHERE plansheet_id = ?
        """,
        (plansheet_id,),
    ).fetchone()
    if row is None:
        return make_default_plan_input(month)
    return _parse_input_row(row_to_dict(row), month)


def _store_input(connection, plansheet_id: int, month: str, plan_input: dict[str, Any]) -> None:
    raw_input_json = json.dumps(plan_input, ensure_ascii=False)
    target_audience_json = json.dumps(plan_input.get("target_audience", []), ensure_ascii=False)
    connection.execute(
        """
        INSERT INTO plansheet_inputs (
            plansheet_id,
            month,
            raw_input_json,
            channel_name,
            category,
            sub_category_name,
            series_name,
            content_type,
            posts_per_week,
            is_series,
            goal,
            tone,
            duration_range_seconds,
            language,
            timezone,
            storage_path,
            special_instructions,
            target_audience_json,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(plansheet_id) DO UPDATE SET
            month = excluded.month,
            raw_input_json = excluded.raw_input_json,
            channel_name = excluded.channel_name,
            category = excluded.category,
            sub_category_name = excluded.sub_category_name,
            series_name = excluded.series_name,
            content_type = excluded.content_type,
            posts_per_week = excluded.posts_per_week,
            is_series = excluded.is_series,
            goal = excluded.goal,
            tone = excluded.tone,
            duration_range_seconds = excluded.duration_range_seconds,
            language = excluded.language,
            timezone = excluded.timezone,
            storage_path = excluded.storage_path,
            special_instructions = excluded.special_instructions,
            target_audience_json = excluded.target_audience_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            plansheet_id,
            month,
            raw_input_json,
            plan_input.get("channel_name", ""),
            plan_input.get("category", ""),
            plan_input.get("sub_category_name", ""),
            plan_input.get("series_name", ""),
            plan_input.get("content_type", ""),
            int(plan_input.get("posts_per_week") or 7),
            1 if plan_input.get("is_series") else 0,
            plan_input.get("goal", ""),
            plan_input.get("tone", ""),
            plan_input.get("duration_range_seconds", ""),
            plan_input.get("language", ""),
            plan_input.get("timezone", ""),
            plan_input.get("storage_path", ""),
            plan_input.get("special_instructions", ""),
            target_audience_json,
        ),
    )


def _replace_rows(connection, plansheet_id: int, rows: list[dict[str, Any]]) -> None:
    connection.execute("DELETE FROM plansheet_rows WHERE plansheet_id = ?", (plansheet_id,))
    for index, row in enumerate(rows, start=1):
        connection.execute(
            """
            INSERT INTO plansheet_rows (
                plansheet_id,
                row_order,
                post_id,
                date_time,
                title,
                description,
                hashtags,
                keywords,
                category,
                sub_category_name,
                series_name,
                episode_number,
                landscape_video_path,
                landscape_thumbnail_path,
                portrait_video_path,
                portrait_thumbnail_path,
                ai_flag,
                kids_flag,
                status,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                plansheet_id,
                index,
                row.get("post_id") or "",
                row.get("date_time") or "",
                row.get("title") or "",
                row.get("description") or "",
                row.get("hashtags") or "",
                row.get("keywords") or "",
                row.get("category") or "",
                row.get("sub_category_name") or "",
                row.get("series_name") or "",
                int(row.get("episode_number") or index),
                row.get("landscape_video_path") or "",
                row.get("landscape_thumbnail_path") or "",
                row.get("portrait_video_path") or "",
                row.get("portrait_thumbnail_path") or "",
                row.get("ai_flag") or "",
                row.get("kids_flag") or "",
                row.get("status") or "",
            ),
        )


def get_plansheet(month: str) -> dict[str, Any]:
    with get_connection() as connection:
        plansheet_id = _fetch_plansheet_id(connection, month)
        if plansheet_id is None:
            return {
                "exists": False,
                "month": month,
                "current_month": _current_month(),
                "columns": REQUIRED_COLUMNS,
                "input": make_default_plan_input(month),
                "rows": [],
                "row_count": 0,
            }

        plan_input = _load_input(connection, plansheet_id, month)
        rows = _load_rows(connection, plansheet_id)
        return {
            "exists": True,
            "month": month,
            "current_month": _current_month(),
            "columns": REQUIRED_COLUMNS,
            "input": plan_input,
            "rows": rows,
            "row_count": len(rows),
        }


def save_plansheet(month: str, plan_input: dict[str, Any] | None, rows: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_input = normalize_input_payload(month, plan_input)
    with get_connection() as connection:
        plansheet_id = _ensure_plansheet_id(connection, month)
        _store_input(connection, plansheet_id, month, normalized_input)
        _replace_rows(connection, plansheet_id, rows)
    return get_plansheet(month)


def delete_plansheet(month: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM plansheets WHERE month = ?", (month,))


def generate_and_save_plansheet(month: str, plan_input: dict[str, Any] | None) -> dict[str, Any]:
    with get_connection() as connection:
        existing_id = _fetch_plansheet_id(connection, month)
        existing_input = _load_input(connection, existing_id, month) if existing_id is not None else make_default_plan_input(month)
        merged_input = normalize_input_payload(month, existing_input)
        if plan_input:
            merged_input = normalize_input_payload(month, {**merged_input, **plan_input})
        plansheet_id = _ensure_plansheet_id(connection, month)
        _store_input(connection, plansheet_id, month, merged_input)

    rows, _ = generate_plansheet_rows(merged_input, month)

    with get_connection() as connection:
        plansheet_id = _ensure_plansheet_id(connection, month)
        _replace_rows(connection, plansheet_id, rows)

    return get_plansheet(month)
