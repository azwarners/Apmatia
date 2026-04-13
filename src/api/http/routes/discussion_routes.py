from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.api.internal import discussions
from src.api.internal.group_access import is_group_member
from src.api.internal.user_management import list_user_groups

from .shared import (
    member_group_ids,
    payload_fields_set,
    require_session,
    serialize_discussion,
    serialize_folder,
)

router = APIRouter()


class PromptPayload(BaseModel):
    prompt: str


class SystemPromptPayload(BaseModel):
    system_prompt: str


class CreateFolderPayload(BaseModel):
    name: str
    parent_id: int | None = None


class UpdateFolderPayload(BaseModel):
    name: str | None = None
    parent_id: int | None = None


class CreateDiscussionPayload(BaseModel):
    title: str
    group_id: int | None = None
    folder_id: int | None = None


class UpdateDiscussionPayload(BaseModel):
    title: str | None = None
    group_id: int | None = None
    folder_id: int | None = None


@router.get("/discussion/state")
def discussion_snapshot(request: Request):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    snapshot = discussions.snapshot(user_id=session.user_id, member_group_ids=group_ids)
    return {
        "discussion_id": snapshot.discussion_id,
        "is_streaming": snapshot.is_streaming,
        "last_error": snapshot.last_error,
        "system_prompt": snapshot.system_prompt,
        "content": snapshot.content,
        "messages": snapshot.messages,
    }


@router.post("/discussion/prompt")
def discussion_prompt(request: Request, payload: PromptPayload):
    session = require_session(request)
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    group_ids = member_group_ids(session.user_id)

    try:
        discussion_id = discussions.start_prompt(
            user_id=session.user_id,
            prompt=prompt,
            member_group_ids=group_ids,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {"status": "started", "discussion_id": discussion_id}


@router.post("/discussion/reset")
def reset_discussion(request: Request):
    session = require_session(request)

    try:
        discussion_id = discussions.reset_discussion(user_id=session.user_id)
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {"status": "reset", "discussion_id": discussion_id}


@router.post("/discussion/system_prompt")
def set_system_prompt(request: Request, payload: SystemPromptPayload):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)

    discussions.set_system_prompt(
        user_id=session.user_id,
        system_prompt=payload.system_prompt,
        member_group_ids=group_ids,
    )
    return {"status": "saved"}


@router.get("/discussions/tree")
def discussions_tree(request: Request):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    tree = discussions.list_tree(user_id=session.user_id, member_group_ids=group_ids)
    return {
        "current_discussion_id": tree.get("current_discussion_id"),
        "folders": [serialize_folder(folder) for folder in tree.get("folders", [])],
        "discussions": [serialize_discussion(discussion) for discussion in tree.get("discussions", [])],
    }


@router.post("/discussions/folders")
def create_discussion_folder(request: Request, payload: CreateFolderPayload):
    session = require_session(request)
    try:
        folder = discussions.create_folder(
            owner_user_id=session.user_id,
            name=payload.name,
            parent_id=payload.parent_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "created", "folder": serialize_folder(folder)}


@router.patch("/discussions/folders/{folder_id}")
def update_discussion_folder(request: Request, folder_id: int, payload: UpdateFolderPayload):
    session = require_session(request)
    provided_fields = payload_fields_set(payload)
    updates: dict = {}
    if "name" in provided_fields:
        updates["name"] = payload.name
    if "parent_id" in provided_fields:
        updates["parent_id"] = payload.parent_id
    if not updates:
        raise HTTPException(status_code=400, detail="No folder updates provided.")
    try:
        folder = discussions.update_folder(
            owner_user_id=session.user_id,
            folder_id=folder_id,
            **updates,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "updated", "folder": serialize_folder(folder)}


@router.delete("/discussions/folders/{folder_id}")
def delete_discussion_folder(request: Request, folder_id: int, force: bool = False):
    session = require_session(request)
    try:
        result = discussions.delete_folder(
            owner_user_id=session.user_id,
            folder_id=folder_id,
            force=force,
        )
    except ValueError as error:
        detail = str(error)
        status_code = 409 if "not empty" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from error
    return {"status": "deleted", "result": result}


@router.post("/discussions/folders/{folder_id}/restore")
def restore_discussion_folder(request: Request, folder_id: int):
    session = require_session(request)
    try:
        result = discussions.restore_folder(
            owner_user_id=session.user_id,
            folder_id=folder_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "restored", "result": result}


@router.post("/discussions/{discussion_id}/restore")
def restore_discussion(request: Request, discussion_id: str):
    session = require_session(request)
    try:
        result = discussions.restore_discussion(
            owner_user_id=session.user_id,
            discussion_id=discussion_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "restored", "result": result}


@router.get("/discussions/trash")
def discussions_trash(request: Request):
    session = require_session(request)
    trash = discussions.list_trash(owner_user_id=session.user_id)
    return {
        "folders": [serialize_folder(folder) for folder in trash.get("folders", [])],
        "discussions": [serialize_discussion(discussion) for discussion in trash.get("discussions", [])],
        "retention_days": 90,
    }


@router.post("/discussions")
def create_discussion_entry(request: Request, payload: CreateDiscussionPayload):
    session = require_session(request)
    if payload.group_id is not None and not is_group_member(
        list_user_groups(session.user_id),
        payload.group_id,
    ):
        raise HTTPException(status_code=403, detail="Group access denied.")

    try:
        discussion = discussions.create_discussion(
            owner_user_id=session.user_id,
            title=payload.title,
            group_id=payload.group_id,
            folder_id=payload.folder_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "created", "discussion": serialize_discussion(discussion)}


@router.patch("/discussions/{discussion_id}")
def update_discussion_entry(request: Request, discussion_id: str, payload: UpdateDiscussionPayload):
    session = require_session(request)
    provided_fields = payload_fields_set(payload)
    updates: dict = {}
    if "title" in provided_fields:
        updates["title"] = payload.title
    if "group_id" in provided_fields:
        updates["group_id"] = payload.group_id
    if "folder_id" in provided_fields:
        updates["folder_id"] = payload.folder_id
    if not updates:
        raise HTTPException(status_code=400, detail="No discussion updates provided.")

    if "group_id" in updates and updates["group_id"] is not None and not is_group_member(
        list_user_groups(session.user_id),
        updates["group_id"],
    ):
        raise HTTPException(status_code=403, detail="Group access denied.")

    try:
        discussion = discussions.update_discussion(
            owner_user_id=session.user_id,
            discussion_id=discussion_id,
            **updates,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "updated", "discussion": serialize_discussion(discussion)}


@router.post("/discussions/{discussion_id}/open")
def open_discussion_entry(request: Request, discussion_id: str):
    session = require_session(request)
    group_ids = member_group_ids(session.user_id)
    try:
        discussions.open_discussion(
            user_id=session.user_id,
            discussion_id=discussion_id,
            member_group_ids=group_ids,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"status": "opened", "discussion_id": discussion_id}
