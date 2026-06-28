from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Path, Request
from pydantic import BaseModel, Field

from src.api.internal.model_management import (
    create_llm_config,
    delete_llm_config,
    list_llm_configs,
    test_llm_config,
    update_llm_config,
)

from .shared import require_session

router = APIRouter(tags=["model-configs"])


class LLMPayload(BaseModel):
    user_alias: str = ""
    backend: str = "openai_compatible"
    provider_name: str = ""
    model_url: str = ""
    api_key: str = ""
    max_response_size: int = 8192
    system_prompt: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


@router.get("/model-configs", response_model=list[dict])
def get_model_configs(request: Request):
    require_session(request)
    return list_llm_configs()


@router.post("/model-configs", response_model=dict)
def create_model_config(request: Request, payload: LLMPayload):
    session = require_session(request)
    return create_llm_config(owner_user_id=session.user_id, **payload.model_dump())


@router.put("/model-configs/{config_id}", response_model=dict)
def update_model_config(
    request: Request,
    config_id: int = Path(..., description="LLM config ID"),
    payload: LLMPayload = Body(...),
):
    require_session(request)
    try:
        return update_llm_config(config_id, **payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/model-configs/{config_id}", response_model=bool)
def delete_model_config(request: Request, config_id: int = Path(..., description="LLM config ID")):
    require_session(request)
    return delete_llm_config(config_id)


@router.post("/model-configs/{config_id}/test", response_model=dict)
def run_model_config_test(
    request: Request,
    config_id: int = Path(..., description="LLM config ID"),
):
    require_session(request)
    try:
        return test_llm_config(config_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
