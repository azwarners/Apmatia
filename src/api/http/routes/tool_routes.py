from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Path, Request
from pydantic import BaseModel, Field

from src.api.internal.tools import (
    assign_tool_to_agent,
    create_tool_definition,
    execute_tool_call,
    get_tool_definition,
    list_agent_tool_assignments,
    list_tool_definitions,
    list_tools_available_to_agent,
    unassign_tool_from_agent,
    update_tool_definition,
)

from .shared import require_session

router = APIRouter(tags=["tools"])


class ToolDefinitionPayload(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    provider_id: str
    enabled: bool = True
    confirmation_required: bool = False
    read_only: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolAssignmentPayload(BaseModel):
    enabled: bool = True
    confirmation_required: bool | None = None
    read_only: bool | None = None


class ToolExecutePayload(BaseModel):
    requester_agent_id: int
    arguments: dict[str, Any] = Field(default_factory=dict)
    discussion_id: str | None = None
    call_id: str | None = None
    approval_granted: bool = False


@router.get("/tools", response_model=list[dict])
def get_tools(request: Request) -> list[dict]:
    require_session(request)
    return list_tool_definitions()


@router.post("/tools", response_model=dict)
def create_tool(request: Request, payload: ToolDefinitionPayload) -> dict:
    session = require_session(request)
    try:
        return create_tool_definition(owner_user_id=session.user_id, **payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/tools/{tool_id}", response_model=dict | None)
def get_tool(
    request: Request,
    tool_id: int = Path(..., description="Tool ID"),
) -> dict | None:
    require_session(request)
    return get_tool_definition(tool_id)


@router.put("/tools/{tool_id}", response_model=dict)
def update_tool(
    request: Request,
    tool_id: int = Path(..., description="Tool ID"),
    payload: ToolDefinitionPayload = Body(...),
) -> dict:
    require_session(request)
    try:
        return update_tool_definition(tool_id, **payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/agents/{agent_id}/tools/{tool_id}", response_model=dict)
def assign_agent_tool(
    request: Request,
    agent_id: int = Path(..., description="Agent ID"),
    tool_id: int = Path(..., description="Tool ID"),
    payload: ToolAssignmentPayload = Body(default_factory=ToolAssignmentPayload),
) -> dict:
    require_session(request)
    try:
        return assign_tool_to_agent(agent_id, tool_id, **payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/agents/{agent_id}/tools/{tool_id}", response_model=bool)
def unassign_agent_tool(
    request: Request,
    agent_id: int = Path(..., description="Agent ID"),
    tool_id: int = Path(..., description="Tool ID"),
) -> bool:
    require_session(request)
    try:
        return unassign_tool_from_agent(agent_id, tool_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/agents/{agent_id}/tools/assignments", response_model=list[dict])
def get_agent_tool_assignments(
    request: Request,
    agent_id: int = Path(..., description="Agent ID"),
) -> list[dict]:
    require_session(request)
    try:
        return list_agent_tool_assignments(agent_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/agents/{agent_id}/tools/available", response_model=list[dict])
def get_tools_available_to_agent(
    request: Request,
    agent_id: int = Path(..., description="Agent ID"),
) -> list[dict]:
    require_session(request)
    try:
        return list_tools_available_to_agent(agent_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/tools/{tool_id}/execute", response_model=dict)
def execute_tool(
    request: Request,
    payload: ToolExecutePayload,
    tool_id: int = Path(..., description="Tool ID"),
) -> dict:
    require_session(request)
    return execute_tool_call(
        tool_id=tool_id,
        arguments=payload.arguments,
        requester_agent_id=payload.requester_agent_id,
        discussion_id=payload.discussion_id,
        call_id=payload.call_id,
        approval_granted=payload.approval_granted,
    )
