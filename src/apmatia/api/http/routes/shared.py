from __future__ import annotations

from fastapi import HTTPException, Request
from pydantic import BaseModel
from apmatia.api.internal.auth import get_session, has_any_users
from apmatia.api.internal.group_access import enabled_group_ids
from apmatia.api.internal.user_management import list_user_groups
from apmatia.core.registry import get_application_registry


def _safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


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
        payload = dict(group)
        payload.setdefault("workspace_root", "")
        return payload
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_by_user_id": group.created_by_user_id,
        "workspace_root": getattr(group, "workspace_root", ""),
        "created_at": group.created_at.isoformat(),
        "updated_at": group.updated_at.isoformat(),
    }


def serialize_membership(membership: object | dict) -> dict:
    if isinstance(membership, dict):
        return membership
    member_kind = getattr(membership, "member_kind", None)
    return {
        "id": membership.id,
        "group_id": membership.group_id,
        "user_id": membership.user_id,
        "agent_id": getattr(membership, "agent_id", None),
        "member_kind": member_kind.value if member_kind is not None else "user",
        "role": membership.role.value,
        "is_enabled": membership.is_enabled,
        "created_at": membership.created_at.isoformat(),
        "updated_at": membership.updated_at.isoformat(),
    }


def serialize_discussion(discussion: object | dict) -> dict:
    if not isinstance(discussion, dict):
        group_id = _safe_int(getattr(discussion, "group_id", None), default=None)
        folder_id = _safe_int(getattr(discussion, "folder_id", None), default=None)
        discussion_id = getattr(discussion, "discussion_id", None)
        if discussion_id is None:
            discussion_id = getattr(discussion, "id", None)
        return {
            "discussion_id": str(discussion_id),
            "title": str(getattr(discussion, "title", "Untitled Discussion")),
            "owner_user_id": _safe_int(getattr(discussion, "owner_user_id", None), default=0),
            "group_id": group_id,
            "visibility": str(getattr(discussion, "visibility", "private")),
            "folder_id": folder_id,
            "focused_wiki_id": getattr(discussion, "focused_wiki_id", None),
            "participant_agent_ids": list(getattr(discussion, "participant_agent_ids", []) or []),
            "chat_mode": str(getattr(discussion, "chat_mode", "round_robin")),
            "chat_pause_seconds": getattr(discussion, "chat_pause_seconds", None),
            "chat_is_paused": bool(getattr(discussion, "chat_is_paused", False)),
            "chat_turn_index": _safe_int(getattr(discussion, "chat_turn_index", 0), default=0),
            "chat_coordinator_agent_id": _safe_int(
                getattr(discussion, "chat_coordinator_agent_id", None), default=None
            ),
            "deleted_at": getattr(discussion, "deleted_at", None),
            "purge_after": getattr(discussion, "purge_after", None),
            "created_at": None
            if getattr(discussion, "created_at", None) is None
            else getattr(discussion, "created_at").isoformat(),
            "updated_at": None
            if getattr(discussion, "updated_at", None) is None
            else getattr(discussion, "updated_at").isoformat(),
        }

    group_id = _safe_int(discussion.get("group_id"), default=None)
    folder_id = _safe_int(discussion.get("folder_id"), default=None)
    discussion_id = discussion.get("discussion_id", discussion.get("id"))
    return {
        "discussion_id": str(discussion_id),
        "title": str(discussion.get("title", "Untitled Discussion")),
        "owner_user_id": _safe_int(discussion.get("owner_user_id"), default=0),
        "group_id": group_id,
        "visibility": str(discussion.get("visibility", "private")),
        "folder_id": folder_id,
        "focused_wiki_id": discussion.get("focused_wiki_id"),
        "participant_agent_ids": list(discussion.get("participant_agent_ids") or []),
        "chat_mode": str(discussion.get("chat_mode", "round_robin")),
        "chat_pause_seconds": discussion.get("chat_pause_seconds"),
        "chat_is_paused": bool(discussion.get("chat_is_paused", False)),
        "chat_turn_index": _safe_int(discussion.get("chat_turn_index"), default=0),
        "chat_coordinator_agent_id": _safe_int(discussion.get("chat_coordinator_agent_id"), default=None),
        "deleted_at": discussion.get("deleted_at"),
        "purge_after": discussion.get("purge_after"),
        "created_at": discussion.get("created_at"),
        "updated_at": discussion.get("updated_at"),
    }


def serialize_folder(folder: dict) -> dict:
    parent_id = _safe_int(folder.get("parent_id"), default=None)
    return {
        "id": _safe_int(folder.get("id"), default=0),
        "name": str(folder.get("name", "")),
        "parent_id": parent_id,
        "owner_user_id": _safe_int(folder.get("owner_user_id"), default=0),
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


def require_active_module(module_id: str):
    def dependency() -> None:
        active_module_ids = {
            module.module_id
            for module in get_application_registry().list_modules(include_development=True)
        }
        if module_id not in active_module_ids:
            raise HTTPException(status_code=404, detail=f"Module is not active: {module_id}")

    return dependency


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
