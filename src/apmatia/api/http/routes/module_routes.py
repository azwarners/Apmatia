from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from apmatia.api.internal.module_management import (
    list_modules,
    get_module_activation_state,
    update_module_visibility,
    update_view_visibility,
    update_view_order,
    update_module_order,
    update_development_modules,
)
from apmatia.api.internal.module_views import (
    get_module_view_document,
    get_module_view_items,
    list_module_commands,
    list_module_view_documents,
    run_module_command,
)
from apmatia.api.internal.view_sources import load_view_source

from .shared import require_session

router = APIRouter(tags=["modules"])


class VisibilityPayload(BaseModel):
    hidden: bool


class ViewOrderPayload(BaseModel):
    new_index: int


class ModuleCommandPayload(BaseModel):
    payload: dict = Field(default_factory=dict)


class DevelopmentModulesPayload(BaseModel):
    enabled: bool


class ViewSourcePayload(BaseModel):
    parameters: dict = Field(default_factory=dict)


@router.get("/module-commands", response_model=list[dict])
def get_module_commands() -> list[dict]:
    """Return the active command catalog used to assemble interface clients."""
    return list_module_commands()


@router.get("/module-view-documents", response_model=list[dict])
def get_view_documents(request: Request) -> list[dict]:
    """Return the portable view contract for every active module view."""
    require_session(request)
    return list_module_view_documents()


@router.post("/module-view-sources/{operation}")
def post_view_source(
    request: Request,
    operation: str = Path(..., description="Declared view source operation"),
    payload: ViewSourcePayload | None = None,
):
    session = require_session(request)
    try:
        return load_view_source(operation, user_id=int(session.user_id), parameters=(payload.parameters if payload else {}))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/modules/activation", response_model=dict)
def get_modules_activation(request: Request) -> dict:
    require_session(request)
    return get_module_activation_state()


@router.put("/modules/activation", response_model=dict)
def put_modules_activation(request: Request, payload: DevelopmentModulesPayload) -> dict:
    require_session(request)
    return update_development_modules(enabled=payload.enabled)


@router.get("/modules", response_model=list[dict])
def get_modules(
    request: Request,
    include_development: bool = Query(False, description="Include development modules in the listing"),
) -> list[dict]:
    require_session(request)
    return list_modules(include_development=include_development)


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


@router.patch("/modules/{module_id}/order", response_model=dict)
def patch_module_order(
    request: Request,
    payload: ViewOrderPayload,
    module_id: str = Path(..., description="Module ID"),
) -> dict:
    require_session(request)
    try:
        return update_module_order(module_id, new_index=payload.new_index)
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


@router.get("/module-views/{view_id}/document", response_model=dict)
def get_view_document(
    request: Request,
    view_id: str = Path(..., description="View ID"),
) -> dict:
    """Return one active module view using the portable view contract."""
    require_session(request)
    try:
        return get_module_view_document(view_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


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
