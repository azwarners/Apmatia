from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from apmatia.api.internal.agent_loops import (
    get_loop_task,
    get_loop_task_transcript,
    list_loop_tasks,
    start_loop_task,
    stop_loop_task,
    wait_for_loop_task,
)

from .shared import member_group_ids, require_session

router = APIRouter(prefix="/agent-loops", tags=["agent-loops"])


class LoopTaskStartPayload(BaseModel):
    contact_kind: Literal["agent", "group"]
    contact_id: int
    title: str = Field(..., description="Task title")
    prompt: str = Field(..., description="Task prompt")
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    participant_agent_ids: list[int] = Field(default_factory=list)
    agent_id: int | None = None
    chat_mode: str = "single"
    allow_tools: bool = True
    max_iterations: int = 10


@router.get("/tasks", response_model=list[dict])
def get_tasks(
    request: Request,
    contact_kind: str | None = Query(default=None),
    contact_id: int | None = Query(default=None),
) -> list[dict]:
    require_session(request)
    return list_loop_tasks(contact_kind=contact_kind, contact_id=contact_id)


@router.post("/tasks", response_model=dict)
def create_task(request: Request, payload: LoopTaskStartPayload) -> dict:
    session = require_session(request)
    return start_loop_task(
        owner_user_id=session.user_id,
        contact_kind=payload.contact_kind,
        contact_id=payload.contact_id,
        title=payload.title,
        prompt=payload.prompt,
        checklist=payload.checklist,
        participant_agent_ids=payload.participant_agent_ids,
        agent_id=payload.agent_id,
        chat_mode=payload.chat_mode,
        allow_tools=payload.allow_tools,
        max_iterations=payload.max_iterations,
        member_group_ids=member_group_ids(session.user_id),
    )


@router.get("/tasks/{task_id}", response_model=dict | None)
def get_task(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
) -> dict | None:
    require_session(request)
    return get_loop_task(task_id)


@router.get("/tasks/{task_id}/transcript", response_model=dict | None)
def get_task_transcript(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
) -> dict | None:
    require_session(request)
    return get_loop_task_transcript(task_id)


@router.post("/tasks/{task_id}/stop", response_model=dict | None)
def stop_task(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
) -> dict | None:
    require_session(request)
    return stop_loop_task(task_id)


@router.post("/tasks/{task_id}/wait", response_model=dict)
def wait_task(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
    timeout: float | None = Body(default=None, description="Seconds to wait"),
) -> dict:
    require_session(request)
    return {"task_id": task_id, "completed": wait_for_loop_task(task_id, timeout=timeout)}
