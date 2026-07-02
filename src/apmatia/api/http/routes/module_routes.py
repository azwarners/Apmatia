from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Request
from pydantic import BaseModel, Field

from apmatia.api.internal.module_management import (
    list_modules,
    update_module_visibility,
    update_view_visibility,
    update_view_order,
)
from apmatia.api.internal.module_views import get_module_view_items, run_module_command

from .shared import require_session

router = APIRouter(tags=["modules"])


class VisibilityPayload(BaseModel):
    hidden: bool


class ViewOrderPayload(BaseModel):
    new_index: int


class ModuleCommandPayload(BaseModel):
    payload: dict = Field(default_factory=dict)


@router.get("/modules", response_model=list[dict])
def get_modules(request: Request) -> list[dict]:
    require_session(request)
    return list_modules()


@router.patch("/modules/{module_id}/visibility", response_model=dict)
def patch_module_visibility(
    request: Request,
    payload: VisibilityPayload,
    module_id: str = Path(..., description="Module ID"),
) -> dict:
    require_session(request)
    try:
        return update_module_visibility(module_id, hidden=payload.hidden)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch("/module-views/{view_id}/visibility", response_model=dict)
def patch_view_visibility(
    request: Request,
    payload: VisibilityPayload,
    view_id: str = Path(..., description="View ID"),
) -> dict:
    require_session(request)
    try:
        return update_view_visibility(view_id, hidden=payload.hidden)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch("/modules/{module_id}/views/{view_id}/order", response_model=dict)
def patch_view_order(
    request: Request,
    payload: ViewOrderPayload,
    module_id: str = Path(..., description="Module ID"),
    view_id: str = Path(..., description="View ID"),
) -> dict:
    require_session(request)
    try:
        return update_view_order(module_id, view_id, new_index=payload.new_index)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/module-views/{view_id}/items", response_model=list[dict])
def get_view_items(
    request: Request,
    view_id: str = Path(..., description="View ID"),
) -> list[dict]:
    session = require_session(request)
    try:
        return get_module_view_items(view_id, user_id=int(session.user_id))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/module-commands/{command_id}", response_model=dict)
def post_module_command(
    request: Request,
    payload: ModuleCommandPayload,
    command_id: str = Path(..., description="Command ID"),
) -> dict:
    session = require_session(request)
    try:
        result = run_module_command(
            command_id,
            payload=payload.payload,
            user_id=int(session.user_id),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return dict(result or {"status": "ok"})
