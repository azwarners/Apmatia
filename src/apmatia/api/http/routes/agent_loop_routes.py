from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from apmatia.api.internal.agent_loops import (
    LoopTaskAccessError,
    archive_conversation_task,
    create_conversation_task,
    decide_conversation_approval,
    get_conversation_task,
    get_loop_task,
    get_loop_task_transcript,
    list_conversation_tasks,
    list_loop_tasks,
    start_loop_task,
    stop_conversation_task,
    submit_conversation_message,
    stop_loop_task,
    wait_for_loop_task,
)

from .shared import member_group_ids, require_active_module, require_session

router = APIRouter(
    prefix="/agent-loops",
    tags=["agent-loops"],
    dependencies=[Depends(require_active_module("agent_loops"))],
)


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


class ConversationTaskCreatePayload(BaseModel):
    model_config = {"extra": "forbid"}
    agent_id: int = Field(..., gt=0)
    title: str = ""


class ConversationMessagePayload(BaseModel):
    model_config = {"extra": "forbid"}
    text: str = Field(..., min_length=1)


class ConversationApprovalPayload(BaseModel):
    model_config = {"extra": "forbid"}
    decision: Literal["approve", "deny"]


@router.get("/tasks", response_model=list[dict])
def get_tasks(
    request: Request,
    agent_id: int = Query(..., gt=0),
) -> list[dict]:
    session = require_session(request)
    try:
        return list_conversation_tasks(
            user_id=session.user_id,
            group_ids=member_group_ids(session.user_id),
            agent_id=agent_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LoopTaskAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/tasks", response_model=dict)
def create_task(request: Request, payload: ConversationTaskCreatePayload) -> dict:
    session = require_session(request)
    try:
        return create_conversation_task(
            user_id=session.user_id,
            group_ids=member_group_ids(session.user_id),
            agent_id=payload.agent_id,
            title=payload.title,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LoopTaskAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/tasks/{task_id}", response_model=dict | None)
def get_task(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
) -> dict | None:
    session = require_session(request)
    try:
        return get_conversation_task(
            task_id=task_id,
            user_id=session.user_id,
            group_ids=member_group_ids(session.user_id),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LoopTaskAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/messages", response_model=dict)
def send_message(
    request: Request,
    payload: ConversationMessagePayload,
    task_id: str = Path(..., description="Task ID"),
) -> dict:
    session = require_session(request)
    try:
        return submit_conversation_message(
            task_id=task_id,
            text=payload.text,
            user_id=session.user_id,
            group_ids=member_group_ids(session.user_id),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LoopTaskAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/transcript", response_model=dict | None)
def get_task_transcript(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
) -> dict | None:
    session = require_session(request)
    try:
        task = get_conversation_task(
            task_id=task_id,
            user_id=session.user_id,
            group_ids=member_group_ids(session.user_id),
        )
        return {"task_id": task_id, "events": task.get("events", [])}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LoopTaskAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/stop", response_model=dict | None)
def stop_task(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
) -> dict | None:
    session = require_session(request)
    try:
        return stop_conversation_task(
            task_id=task_id,
            user_id=session.user_id,
            group_ids=member_group_ids(session.user_id),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LoopTaskAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/archive", response_model=dict)
def archive_task(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
) -> dict:
    session = require_session(request)
    try:
        result = archive_conversation_task(
            task_id=task_id,
            user_id=session.user_id,
            group_ids=member_group_ids(session.user_id),
        )
        if result is None:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LoopTaskAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/approval", response_model=dict)
def decide_approval(
    request: Request,
    payload: ConversationApprovalPayload,
    task_id: str = Path(..., description="Task ID"),
) -> dict:
    session = require_session(request)
    try:
        result = decide_conversation_approval(
            task_id=task_id,
            decision=payload.decision,
            user_id=session.user_id,
            group_ids=member_group_ids(session.user_id),
        )
        if result is None:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LoopTaskAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/wait", response_model=dict)
def wait_task(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
    timeout: float | None = Body(default=None, description="Seconds to wait"),
) -> dict:
    session = require_session(request)
    try:
        get_conversation_task(
            task_id=task_id,
            user_id=session.user_id,
            group_ids=member_group_ids(session.user_id),
        )
        return {"task_id": task_id, "completed": wait_for_loop_task(task_id, timeout=timeout)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LoopTaskAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
