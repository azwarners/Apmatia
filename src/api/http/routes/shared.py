from __future__ import annotations

from fastapi import HTTPException, Request
from pydantic import BaseModel
from src.api.internal.auth import get_session, has_any_users
from src.api.internal.group_access import enabled_group_ids
from src.api.internal.user_management import list_user_groups


def serialize_user(user: object | dict) -> dict:
    if isinstance(user, dict):
        return user
    return {
        "id": user.id,
        "username": user.username,
        "is_enabled": user.is_enabled,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def serialize_group(group: object | dict) -> dict:
    if isinstance(group, dict):
        return group
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_by_user_id": group.created_by_user_id,
        "created_at": group.created_at.isoformat(),
        "updated_at": group.updated_at.isoformat(),
    }


def serialize_membership(membership: object | dict) -> dict:
    if isinstance(membership, dict):
        return membership
    return {
        "id": membership.id,
        "group_id": membership.group_id,
        "user_id": membership.user_id,
        "role": membership.role.value,
        "is_enabled": membership.is_enabled,
        "created_at": membership.created_at.isoformat(),
        "updated_at": membership.updated_at.isoformat(),
    }


def serialize_discussion(discussion: dict) -> dict:
    return {
        "discussion_id": str(discussion.get("discussion_id")),
        "title": str(discussion.get("title", "Untitled Discussion")),
        "owner_user_id": int(discussion.get("owner_user_id", 0)),
        "group_id": None if discussion.get("group_id") is None else int(discussion.get("group_id")),
        "visibility": str(discussion.get("visibility", "private")),
        "folder_id": None if discussion.get("folder_id") is None else int(discussion.get("folder_id")),
        "deleted_at": discussion.get("deleted_at"),
        "purge_after": discussion.get("purge_after"),
        "created_at": discussion.get("created_at"),
        "updated_at": discussion.get("updated_at"),
    }


def serialize_folder(folder: dict) -> dict:
    return {
        "id": int(folder.get("id", 0)),
        "name": str(folder.get("name", "")),
        "parent_id": None if folder.get("parent_id") is None else int(folder.get("parent_id")),
        "owner_user_id": int(folder.get("owner_user_id", 0)),
        "deleted_at": folder.get("deleted_at"),
        "purge_after": folder.get("purge_after"),
        "created_at": folder.get("created_at"),
        "updated_at": folder.get("updated_at"),
    }


def session_payload(request: Request) -> dict:
    token = request.cookies.get("apmatia_session")
    session = get_session(token)
    return {
        "authenticated": session is not None,
        "user_id": None if session is None else session.user_id,
        "username": None if session is None else session.username,
        "has_users": has_any_users(),
    }


def require_session(request: Request):
    token = request.cookies.get("apmatia_session")
    session = get_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return session


def member_group_ids(user_id: int) -> set[int]:
    return enabled_group_ids(list_user_groups(user_id))


def payload_fields_set(payload: BaseModel) -> set[str]:
    model_fields_set = getattr(payload, "model_fields_set", None)
    if model_fields_set is not None:
        return {str(field) for field in model_fields_set}
    legacy_fields_set = getattr(payload, "__fields_set__", None)
    if legacy_fields_set is not None:
        return {str(field) for field in legacy_fields_set}
    return set()
