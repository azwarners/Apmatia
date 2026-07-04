from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Path, Request
from pydantic import BaseModel, Field

from apmatia.api.internal.ai_model_manager import (
    create_ai_model,
    create_task_preference,
    delete_ai_model,
    delete_task_preference,
    list_ai_models,
    list_task_preferences,
    scan_ai_models,
    show_ai_model,
    update_ai_model,
    update_task_preference,
)

from .shared import require_session

router = APIRouter(tags=["ai-model-manager"])


class GGUFModelPayload(BaseModel):
    name: str = ""
    local_path: str = ""
    file_size_bytes: int = 0
    estimated_ram_bytes: int = 0
    estimated_vram_bytes: int = 0
    size_class: str = ""
    cost_mode: str = "free"
    input_token_cost_per_1k: float | None = None
    output_token_cost_per_1k: float | None = None
    notes: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


class GGUFModelUpdatePayload(BaseModel):
    name: str | None = None
    local_path: str | None = None
    file_size_bytes: int | None = None
    estimated_ram_bytes: int | None = None
    estimated_vram_bytes: int | None = None
    size_class: str | None = None
    cost_mode: str | None = None
    input_token_cost_per_1k: float | None = None
    output_token_cost_per_1k: float | None = None
    notes: str | None = None
    metadata: dict[str, str] | None = None


class GGUFScanPayload(BaseModel):
    directory: str
    recursive: bool = True


class TaskPreferencePayload(BaseModel):
    task_name: str = ""
    preferred_size_classes: list[str] = Field(default_factory=list)
    notes: str = ""


class TaskPreferenceUpdatePayload(BaseModel):
    task_name: str | None = None
    preferred_size_classes: list[str] | None = None
    notes: str | None = None


@router.get("/ai-models", response_model=list[dict])
def get_ai_models(request: Request) -> list[dict]:
    require_session(request)
    return list_ai_models()


@router.post("/ai-models", response_model=dict)
def post_ai_model(request: Request, payload: GGUFModelPayload):
    require_session(request)
    try:
        return create_ai_model(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/ai-models/scan", response_model=dict)
def scan_ai_models_route(request: Request, payload: GGUFScanPayload):
    require_session(request)
    try:
        return scan_ai_models(payload.directory, recursive=payload.recursive)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/ai-models/{model_id}", response_model=dict)
def get_ai_model(request: Request, model_id: int = Path(..., description="GGUF model ID")):
    require_session(request)
    try:
        return show_ai_model(model_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.put("/ai-models/{model_id}", response_model=dict)
def put_ai_model(
    request: Request,
    model_id: int = Path(..., description="GGUF model ID"),
    payload: GGUFModelUpdatePayload = Body(...),
):
    require_session(request)
    try:
        return update_ai_model(model_id, **payload.model_dump(exclude_none=True))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/ai-models/{model_id}", response_model=bool)
def delete_ai_model_route(request: Request, model_id: int = Path(..., description="GGUF model ID")):
    require_session(request)
    return delete_ai_model(model_id)


@router.get("/ai-model-preferences", response_model=list[dict])
def get_ai_model_preferences(request: Request) -> list[dict]:
    require_session(request)
    return list_task_preferences()


@router.post("/ai-model-preferences", response_model=dict)
def post_ai_model_preference(request: Request, payload: TaskPreferencePayload):
    require_session(request)
    try:
        return create_task_preference(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put("/ai-model-preferences/{preference_id}", response_model=dict)
def put_ai_model_preference(
    request: Request,
    preference_id: int = Path(..., description="Task preference ID"),
    payload: TaskPreferenceUpdatePayload = Body(...),
):
    require_session(request)
    try:
        return update_task_preference(preference_id, **payload.model_dump(exclude_none=True))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/ai-model-preferences/{preference_id}", response_model=bool)
def delete_ai_model_preference(
    request: Request,
    preference_id: int = Path(..., description="Task preference ID"),
):
    require_session(request)
    return delete_task_preference(preference_id)
