from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from apmatia.api.internal.ai_model_executor import (
    can_ai_model_run,
    get_ai_model_execution_status,
    get_ai_model_executor_resources,
    list_ai_model_executions,
    start_ai_model_execution,
    stop_ai_model_execution,
)

from .shared import require_session

router = APIRouter(tags=["ai-model-executor"])


class ModelExecutionStartPayload(BaseModel):
    host_id: str = "local"
    runtime_id: str | None = None
    port: int | None = None
    stop_conflicting_models: bool | None = None
    launch_args: list[str] = Field(default_factory=list)


class ModelExecutionStopPayload(BaseModel):
    host_id: str = "local"
    runtime_id: str | None = None
    execution_id: int | None = None


@router.get("/ai-model-executor/resources", response_model=dict)
def get_resources(request: Request) -> dict:
    require_session(request)
    return get_ai_model_executor_resources()


@router.get("/ai-model-executor/can-run/{model_id}", response_model=dict)
def get_can_run(request: Request, model_id: int = Path(..., description="GGUF model ID")):
    require_session(request)
    try:
        return can_ai_model_run(model_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/ai-model-executions", response_model=list[dict])
def get_executions(request: Request, model_id: int | None = Query(default=None)):
    require_session(request)
    return list_ai_model_executions(model_id=model_id)


@router.get("/ai-model-executions/status", response_model=dict)
def get_execution_status(request: Request, model_id: int | None = Query(default=None)):
    require_session(request)
    return get_ai_model_execution_status(model_id=model_id)


@router.post("/ai-model-executor/start/{model_id}", response_model=dict)
def post_start_model(request: Request, model_id: int = Path(..., description="GGUF model ID"), payload: ModelExecutionStartPayload = Body(...)):
    require_session(request)
    try:
        return start_ai_model_execution(model_id, **payload.model_dump(exclude_none=True))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/ai-model-executor/stop/{model_id}", response_model=dict)
def post_stop_model(request: Request, model_id: int = Path(..., description="GGUF model ID"), payload: ModelExecutionStopPayload = Body(...)):
    require_session(request)
    return stop_ai_model_execution(model_id, **payload.model_dump(exclude_none=True))
