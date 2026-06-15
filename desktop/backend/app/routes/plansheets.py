from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..defaults import REQUIRED_COLUMNS
from ..services.plansheet_service import (
    delete_plansheet,
    generate_and_save_plansheet,
    get_plansheet,
    save_plansheet,
)

router = APIRouter(prefix="/api/plansheets", tags=["plansheets"])


@router.get("/{month}")
def read_plansheet(month: str) -> dict[str, Any]:
    if not month or len(month) != 7 or month[4] != "-":
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")
    return get_plansheet(month)


@router.put("/{month}")
def update_plansheet(month: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not month or len(month) != 7 or month[4] != "-":
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")

    plan_input = payload.get("input") or payload.get("plan_input") or {}
    rows = payload.get("rows") or []
    columns = payload.get("columns") or REQUIRED_COLUMNS
    if columns != REQUIRED_COLUMNS:
        columns = REQUIRED_COLUMNS
    return save_plansheet(month, plan_input, rows)


@router.post("/{month}/generate")
def generate_plansheet(month: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not month or len(month) != 7 or month[4] != "-":
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")

    plan_input = (payload or {}).get("input") or (payload or {}).get("plan_input") or {}
    try:
        return generate_and_save_plansheet(month, plan_input)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{month}")
def remove_plansheet(month: str) -> dict[str, Any]:
    if not month or len(month) != 7 or month[4] != "-":
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")
    delete_plansheet(month)
    return {"ok": True}
