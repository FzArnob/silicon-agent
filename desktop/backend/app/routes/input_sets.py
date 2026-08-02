from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..services.input_set_service import (
    InputSetError,
    create_input_set,
    delete_input_set,
    list_input_sets,
    update_input_set,
)

router = APIRouter(prefix="/api/input-sets", tags=["input-sets"])


@router.get("")
def read_input_sets() -> list[dict[str, Any]]:
    return list_input_sets()


@router.post("")
def add_input_set(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return create_input_set(payload)
    except InputSetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{set_id}")
def edit_input_set(set_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return update_input_set(set_id, payload)
    except InputSetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{set_id}")
def remove_input_set(set_id: int) -> dict[str, bool]:
    try:
        delete_input_set(set_id)
    except InputSetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}
