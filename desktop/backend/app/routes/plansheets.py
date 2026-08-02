from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException

from ..services.plansheet_service import (
    PlansheetError,
    delete_plansheet,
    generate_and_save_plansheet,
    get_plansheet,
    save_plansheet,
    set_plansheet_input_set,
)

router = APIRouter(prefix="/api/plansheets", tags=["plansheets"])

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _validate_month(month: str) -> None:
    if not MONTH_PATTERN.match(month or ""):
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")


@router.get("/{month}")
def read_plansheet(month: str) -> dict[str, Any]:
    _validate_month(month)
    return get_plansheet(month)


@router.put("/{month}")
def update_plansheet(month: str, payload: dict[str, Any]) -> dict[str, Any]:
    _validate_month(month)
    try:
        return save_plansheet(month, payload.get("input_set_id"), payload.get("rows") or [])
    except PlansheetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{month}/input-set")
def select_input_set(month: str, payload: dict[str, Any]) -> dict[str, Any]:
    _validate_month(month)
    try:
        return set_plansheet_input_set(month, payload.get("input_set_id"))
    except PlansheetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{month}/generate")
def generate_plansheet(month: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _validate_month(month)
    try:
        return generate_and_save_plansheet(month, (payload or {}).get("input_set_id"))
    except PlansheetError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/{month}")
def remove_plansheet(month: str) -> dict[str, bool]:
    _validate_month(month)
    delete_plansheet(month)
    return {"ok": True}
