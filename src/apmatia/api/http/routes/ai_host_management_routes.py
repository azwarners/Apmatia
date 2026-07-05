from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Path, Request
from pydantic import BaseModel, ConfigDict

from apmatia.api.internal.ai_host_management import (
    create_ai_host,
    delete_ai_host,
    disable_ai_host,
    inspect_ai_host_resources,
    list_ai_hosts,
    show_ai_host,
    update_ai_host,
    validate_ai_host,
)

from .shared import require_session

router = APIRouter(tags=["ai-host-management"])


class AIHostCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    hostname: str = ""
    role: str = ""
    connection_type: str = "local"
    username: str = ""
    port: int = 22
    credential_ref: str = ""
    enabled: bool = True
    notes: str = ""


class AIHostUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    hostname: str | None = None
    role: str | None = None
    connection_type: str | None = None
    username: str | None = None
    port: int | None = None
    credential_ref: str | None = None
    enabled: bool | None = None
    notes: str | None = None


class AIHostValidationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    hostname: str = ""
    role: str = ""
    connection_type: str = "local"
    username: str = ""
    port: int = 22
    credential_ref: str = ""
    enabled: bool = True
    notes: str = ""


@router.get("/ai-hosts", response_model=list[dict])
def get_ai_hosts(request: Request) -> list[dict]:
    require_session(request)
    return list_ai_hosts()


@router.post("/ai-hosts", response_model=dict)
def post_ai_host(request: Request, payload: AIHostCreatePayload):
    require_session(request)
    try:
        return create_ai_host(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/ai-hosts/{host_id}", response_model=dict)
def get_ai_host(request: Request, host_id: int = Path(..., description="AI host ID")):
    require_session(request)
    try:
        return show_ai_host(host_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.put("/ai-hosts/{host_id}", response_model=dict)
def put_ai_host(
    request: Request,
    host_id: int = Path(..., description="AI host ID"),
    payload: AIHostUpdatePayload = Body(...),
):
    require_session(request)
    try:
        return update_ai_host(host_id, **payload.model_dump(exclude_none=True))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/ai-hosts/{host_id}/disable", response_model=dict)
def post_disable_ai_host(request: Request, host_id: int = Path(..., description="AI host ID")):
    require_session(request)
    try:
        return disable_ai_host(host_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/ai-hosts/{host_id}", response_model=dict)
def delete_ai_host_route(request: Request, host_id: int = Path(..., description="AI host ID")):
    require_session(request)
    try:
        return delete_ai_host(host_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/ai-host-resources", response_model=list[dict])
def get_ai_host_resources(request: Request) -> list[dict]:
    require_session(request)
    return inspect_ai_host_resources()


@router.post("/ai-hosts/validate", response_model=dict)
def post_validate_ai_host(request: Request, payload: AIHostValidationPayload):
    require_session(request)
    try:
        return validate_ai_host(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
