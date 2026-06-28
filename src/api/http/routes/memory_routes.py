from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from src.api.internal.memory_management import (
    archive_memory,
    create_memory,
    delete_memory,
    get_memory,
    list_memories,
    search_memories,
    update_memory,
)
from src.core.agent_management_runtime import get_agent_manager

from .shared import member_group_ids, payload_fields_set, require_session

router = APIRouter(tags=["memories"])


class MemoryCreatePayload(BaseModel):
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    owner_group_id: int | None = None
    owner_agent_id: int | None = None
    mode: int = 0o000
    created_by_agent_id: int | None = None
    source_discussion_id: str | None = None
    source_message_ids: list[str] = Field(default_factory=list)
    visibility: str = "draft"
    status: str = "active"


class MemoryUpdatePayload(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    owner_group_id: int | None = None
    owner_agent_id: int | None = None
    mode: int | None = None
    created_by_agent_id: int | None = None
    source_discussion_id: str | None = None
    source_message_ids: list[str] | None = None
    visibility: str | None = None
    status: str | None = None


@router.get("/memories", response_model=list[dict[str, Any]])
def get_memories(
    request: Request,
    owner_user_id: int | None = Query(None),
    owner_group_id: int | None = Query(None),
    owner_agent_id: int | None = Query(None),
    visibility: str | None = Query(None),
    status: str | None = Query(None),
    source_discussion_id: str | None = Query(None),
    include_archived: bool = Query(False),
    include_deleted: bool = Query(False),
    limit: int | None = Query(None),
) -> list[dict[str, Any]]:
    session = require_session(request)
    return list_memories(
        requester_user_id=session.user_id,
        requester_group_ids=member_group_ids(session.user_id),
        owner_user_id=owner_user_id,
        owner_group_id=owner_group_id,
        owner_agent_id=owner_agent_id,
        visibility=visibility,
        status=status,
        source_discussion_id=source_discussion_id,
        include_archived=include_archived,
        include_deleted=include_deleted,
        limit=limit,
    )


@router.get("/memories/search", response_model=list[dict[str, Any]])
def search_memory_items(
    request: Request,
    query: str = Query(""),
    owner_user_id: int | None = Query(None),
    owner_group_id: int | None = Query(None),
    owner_agent_id: int | None = Query(None),
    visibility: str | None = Query(None),
    status: str | None = Query(None),
    source_discussion_id: str | None = Query(None),
    include_archived: bool = Query(False),
    include_deleted: bool = Query(False),
    limit: int | None = Query(None),
) -> list[dict[str, Any]]:
    session = require_session(request)
    return search_memories(
        query,
        requester_user_id=session.user_id,
        requester_group_ids=member_group_ids(session.user_id),
        owner_user_id=owner_user_id,
        owner_group_id=owner_group_id,
        owner_agent_id=owner_agent_id,
        visibility=visibility,
        status=status,
        source_discussion_id=source_discussion_id,
        include_archived=include_archived,
        include_deleted=include_deleted,
        limit=limit,
    )


@router.get("/memories/{memory_id}", response_model=dict[str, Any] | None)
def get_memory_item(request: Request, memory_id: int = Path(...)) -> dict[str, Any] | None:
    session = require_session(request)
    return get_memory(
        memory_id,
        requester_user_id=session.user_id,
        requester_group_ids=member_group_ids(session.user_id),
    )


@router.post("/memories", response_model=dict[str, Any])
def create_memory_item(request: Request, payload: MemoryCreatePayload = Body(...)) -> dict[str, Any]:
    session = require_session(request)
    session_group_ids = member_group_ids(session.user_id)
    _validate_owner_agent(
        session_user_id=session.user_id,
        session_group_ids=session_group_ids,
        owner_agent_id=payload.owner_agent_id,
    )
    try:
        return create_memory(
            payload.title,
            payload.content,
            tags=payload.tags,
            owner_user_id=session.user_id,
            owner_group_id=payload.owner_group_id,
            owner_agent_id=payload.owner_agent_id,
            mode=payload.mode,
            created_by_agent_id=payload.created_by_agent_id,
            source_discussion_id=payload.source_discussion_id,
            source_message_ids=payload.source_message_ids,
            visibility=payload.visibility,
            status=payload.status,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put("/memories/{memory_id}", response_model=dict[str, Any])
def update_memory_item(
    request: Request,
    memory_id: int = Path(...),
    payload: MemoryUpdatePayload = Body(...),
) -> dict[str, Any]:
    session = require_session(request)
    provided_fields = payload_fields_set(payload)
    if "owner_agent_id" in provided_fields:
        _validate_owner_agent(
            session_user_id=session.user_id,
            session_group_ids=member_group_ids(session.user_id),
            owner_agent_id=payload.owner_agent_id,
        )
    updates = {}
    for field in provided_fields:
        updates[field] = getattr(payload, field)
    try:
        return update_memory(
            memory_id,
            requester_user_id=session.user_id,
            requester_group_ids=member_group_ids(session.user_id),
            **updates,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/memories/{memory_id}/archive", response_model=dict[str, Any])
def archive_memory_item(request: Request, memory_id: int = Path(...)) -> dict[str, Any]:
    session = require_session(request)
    try:
        return archive_memory(
            memory_id,
            requester_user_id=session.user_id,
            requester_group_ids=member_group_ids(session.user_id),
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/memories/{memory_id}", response_model=dict[str, Any])
def delete_memory_item(request: Request, memory_id: int = Path(...)) -> dict[str, Any]:
    session = require_session(request)
    try:
        return delete_memory(
            memory_id,
            requester_user_id=session.user_id,
            requester_group_ids=member_group_ids(session.user_id),
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _validate_owner_agent(
    *,
    session_user_id: int,
    session_group_ids: set[int],
    owner_agent_id: int | None,
) -> None:
    if owner_agent_id is None:
        return
    agent = get_agent_manager().get_agent(int(owner_agent_id))
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {owner_agent_id}")
    if agent.owner_user_id == session_user_id:
        return
    if agent.owner_group_id is not None and agent.owner_group_id in session_group_ids:
        return
    raise HTTPException(status_code=403, detail="Agent access denied.")
