from fastapi import APIRouter, HTTPException
from fastapi import Request, Response
from pydantic import BaseModel
from src.api.internal.auth import get_session, has_any_users, login_user, logout_session, register_user
from src.api.internal.user_management import (
    add_member,
    create_group,
    create_user,
    delete_group,
    delete_user,
    edit_user,
    list_groups,
    list_group_members,
    list_user_groups,
    list_users,
    verify_user,
)
from src.api.internal.prompt_LLM import prompt_llm
from src.core.app_config import get_config_value, set_config_value
from src.core.discussions import discussion_state
from src.core.user_management.models import Group, GroupMembership, GroupRole, User

router = APIRouter()


class PromptPayload(BaseModel):
    prompt: str


class SystemPromptPayload(BaseModel):
    system_prompt: str


class SettingsPayload(BaseModel):
    model_url: str
    max_response_size: int
    system_prompt: str
    theme: str = "dark"
    font_family: str = "system-ui"
    font_size: int = 16
    title_bar_height: int = 56
    title_bar_font_size: int = 20


class CreateUserPayload(BaseModel):
    username: str
    password: str


class VerifyUserPayload(BaseModel):
    username: str
    password: str


class EditUserPayload(BaseModel):
    username: str | None = None
    password: str | None = None
    is_enabled: bool | None = None


class CreateGroupPayload(BaseModel):
    name: str
    created_by_user_id: int
    description: str = ""


class AddMemberPayload(BaseModel):
    user_id: int
    role: GroupRole = GroupRole.MEMBER


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


class AuthPayload(BaseModel):
    username: str
    password: str


def _serialize_user(user: User | dict) -> dict:
    if isinstance(user, dict):
        return user
    return {
        "id": user.id,
        "username": user.username,
        "is_enabled": user.is_enabled,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def _serialize_group(group: Group | dict) -> dict:
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


def _serialize_membership(membership: GroupMembership | dict) -> dict:
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


def _serialize_discussion(discussion: dict) -> dict:
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


def _serialize_folder(folder: dict) -> dict:
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


def _session_payload(request: Request) -> dict:
    token = request.cookies.get("apmatia_session")
    session = get_session(token)
    return {
        "authenticated": session is not None,
        "user_id": None if session is None else session.user_id,
        "username": None if session is None else session.username,
        "has_users": has_any_users(),
    }


def _require_session(request: Request):
    token = request.cookies.get("apmatia_session")
    session = get_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return session


def _is_group_member(group_id: int, user_id: int) -> bool:
    memberships = list_user_groups(user_id)
    for membership in memberships:
        m_group_id = membership["group_id"] if isinstance(membership, dict) else membership.group_id
        m_enabled = membership.get("is_enabled", True) if isinstance(membership, dict) else membership.is_enabled
        if int(m_group_id) == group_id and bool(m_enabled):
            return True
    return False


def _is_group_owner(group_id: int, user_id: int) -> bool:
    memberships = list_group_members(group_id)
    for membership in memberships:
        m_user_id = membership["user_id"] if isinstance(membership, dict) else membership.user_id
        m_role = membership["role"] if isinstance(membership, dict) else membership.role.value
        m_enabled = membership.get("is_enabled", True) if isinstance(membership, dict) else membership.is_enabled
        if int(m_user_id) == user_id and str(m_role) == GroupRole.OWNER.value and bool(m_enabled):
            return True
    return False


@router.get("/prompt")
def prompt(request: Request, prompt: str = "Hello", output_dir: str | None = None):
    _require_session(request)
    return {"message": prompt_llm(prompt, output_dir=output_dir)}


@router.get("/discussion/state")
def discussion_snapshot(request: Request):
    session = _require_session(request)
    member_group_ids = {
        int(m["group_id"]) if isinstance(m, dict) else int(m.group_id)
        for m in list_user_groups(session.user_id)
        if (m.get("is_enabled", True) if isinstance(m, dict) else m.is_enabled)
    }
    snapshot = discussion_state.snapshot(user_id=session.user_id, member_group_ids=member_group_ids)
    return {
        "discussion_id": snapshot.discussion_id,
        "is_streaming": snapshot.is_streaming,
        "last_error": snapshot.last_error,
        "system_prompt": snapshot.system_prompt,
        "content": snapshot.content,
    }


@router.post("/discussion/prompt")
def discussion_prompt(request: Request, payload: PromptPayload):
    session = _require_session(request)
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    member_group_ids = {
        int(m["group_id"]) if isinstance(m, dict) else int(m.group_id)
        for m in list_user_groups(session.user_id)
        if (m.get("is_enabled", True) if isinstance(m, dict) else m.is_enabled)
    }

    try:
        discussion_id = discussion_state.start_prompt(
            user_id=session.user_id,
            prompt=prompt,
            member_group_ids=member_group_ids,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {"status": "started", "discussion_id": discussion_id}


@router.post("/discussion/reset")
def reset_discussion(request: Request):
    session = _require_session(request)

    try:
        discussion_id = discussion_state.reset_discussion(user_id=session.user_id)
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {"status": "reset", "discussion_id": discussion_id}


@router.post("/discussion/system_prompt")
def set_system_prompt(request: Request, payload: SystemPromptPayload):
    session = _require_session(request)
    member_group_ids = {
        int(m["group_id"]) if isinstance(m, dict) else int(m.group_id)
        for m in list_user_groups(session.user_id)
        if (m.get("is_enabled", True) if isinstance(m, dict) else m.is_enabled)
    }

    discussion_state.set_system_prompt(
        user_id=session.user_id,
        system_prompt=payload.system_prompt,
        member_group_ids=member_group_ids,
    )
    return {"status": "saved"}


@router.get("/discussions/tree")
def discussions_tree(request: Request):
    session = _require_session(request)
    member_group_ids = {
        int(m["group_id"]) if isinstance(m, dict) else int(m.group_id)
        for m in list_user_groups(session.user_id)
        if (m.get("is_enabled", True) if isinstance(m, dict) else m.is_enabled)
    }
    tree = discussion_state.list_tree(user_id=session.user_id, member_group_ids=member_group_ids)
    return {
        "current_discussion_id": tree.get("current_discussion_id"),
        "folders": [_serialize_folder(folder) for folder in tree.get("folders", [])],
        "discussions": [_serialize_discussion(discussion) for discussion in tree.get("discussions", [])],
    }


@router.post("/discussions/folders")
def create_discussion_folder(request: Request, payload: CreateFolderPayload):
    session = _require_session(request)
    try:
        folder = discussion_state.create_folder(
            owner_user_id=session.user_id,
            name=payload.name,
            parent_id=payload.parent_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "created", "folder": _serialize_folder(folder)}


@router.patch("/discussions/folders/{folder_id}")
def update_discussion_folder(request: Request, folder_id: int, payload: UpdateFolderPayload):
    session = _require_session(request)
    try:
        folder = discussion_state.update_folder(
            owner_user_id=session.user_id,
            folder_id=folder_id,
            name=payload.name,
            parent_id=payload.parent_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "updated", "folder": _serialize_folder(folder)}


@router.delete("/discussions/folders/{folder_id}")
def delete_discussion_folder(request: Request, folder_id: int, force: bool = False):
    session = _require_session(request)
    try:
        result = discussion_state.delete_folder(
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
    session = _require_session(request)
    try:
        result = discussion_state.restore_folder(
            owner_user_id=session.user_id,
            folder_id=folder_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "restored", "result": result}


@router.post("/discussions/{discussion_id}/restore")
def restore_discussion(request: Request, discussion_id: str):
    session = _require_session(request)
    try:
        result = discussion_state.restore_discussion(
            owner_user_id=session.user_id,
            discussion_id=discussion_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "restored", "result": result}


@router.get("/discussions/trash")
def discussions_trash(request: Request):
    session = _require_session(request)
    trash = discussion_state.list_trash(owner_user_id=session.user_id)
    return {
        "folders": [_serialize_folder(folder) for folder in trash.get("folders", [])],
        "discussions": [_serialize_discussion(discussion) for discussion in trash.get("discussions", [])],
        "retention_days": 90,
    }


@router.post("/discussions")
def create_discussion_entry(request: Request, payload: CreateDiscussionPayload):
    session = _require_session(request)
    if payload.group_id is not None and not _is_group_member(payload.group_id, session.user_id):
        raise HTTPException(status_code=403, detail="Group access denied.")

    try:
        discussion = discussion_state.create_discussion(
            owner_user_id=session.user_id,
            title=payload.title,
            group_id=payload.group_id,
            folder_id=payload.folder_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "created", "discussion": _serialize_discussion(discussion)}


@router.patch("/discussions/{discussion_id}")
def update_discussion_entry(request: Request, discussion_id: str, payload: UpdateDiscussionPayload):
    session = _require_session(request)
    if payload.group_id is not None and not _is_group_member(payload.group_id, session.user_id):
        raise HTTPException(status_code=403, detail="Group access denied.")

    try:
        discussion = discussion_state.update_discussion(
            owner_user_id=session.user_id,
            discussion_id=discussion_id,
            title=payload.title,
            group_id=payload.group_id,
            folder_id=payload.folder_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "updated", "discussion": _serialize_discussion(discussion)}


@router.post("/discussions/{discussion_id}/open")
def open_discussion_entry(request: Request, discussion_id: str):
    session = _require_session(request)
    member_group_ids = {
        int(m["group_id"]) if isinstance(m, dict) else int(m.group_id)
        for m in list_user_groups(session.user_id)
        if (m.get("is_enabled", True) if isinstance(m, dict) else m.is_enabled)
    }
    try:
        discussion_state.open_discussion(
            user_id=session.user_id,
            discussion_id=discussion_id,
            member_group_ids=member_group_ids,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"status": "opened", "discussion_id": discussion_id}


@router.get("/settings")
def get_settings(request: Request):
    _require_session(request)
    backend_name = (
        get_config_value("llm", "backend", default=None) or "openai_compatible"
    ).strip().lower()
    if backend_name in {"koboldcpp", "kobold_cpp"}:
        model_url = get_config_value("llm", "koboldcpp", "base_url", default=None)
    else:
        model_url = get_config_value(
            "llm", "openai_compatible", "base_url", default=None
        )

    max_tokens = get_config_value("llm", "max_tokens", default=8192)
    system_prompt = get_config_value("discussion", "system_prompt", default="")
    theme = get_config_value("ui", "theme", default="dark")
    font_family = get_config_value("ui", "font_family", default="system-ui")
    font_size = get_config_value("ui", "font_size", default=16)
    title_bar_height = get_config_value("ui", "title_bar_height", default=56)
    title_bar_font_size = get_config_value("ui", "title_bar_font_size", default=20)
    return {
        "backend": backend_name,
        "model_url": str(model_url or ""),
        "max_response_size": int(max_tokens),
        "system_prompt": str(system_prompt or ""),
        "theme": str(theme or "dark"),
        "font_family": str(font_family or "system-ui"),
        "font_size": int(font_size),
        "title_bar_height": int(title_bar_height),
        "title_bar_font_size": int(title_bar_font_size),
    }


@router.post("/settings")
def save_settings(request: Request, payload: SettingsPayload):
    session = _require_session(request)
    model_url = payload.model_url.strip()
    system_prompt = payload.system_prompt

    if not model_url:
        raise HTTPException(status_code=400, detail="Model URL cannot be empty.")
    if payload.max_response_size < 1:
        raise HTTPException(
            status_code=400, detail="Max response size must be at least 1."
        )
    if payload.theme not in {"dark", "light"}:
        raise HTTPException(status_code=400, detail="Theme must be 'dark' or 'light'.")
    if payload.font_size < 12 or payload.font_size > 24:
        raise HTTPException(
            status_code=400, detail="Font size must be between 12 and 24."
        )
    if payload.title_bar_height < 40 or payload.title_bar_height > 96:
        raise HTTPException(
            status_code=400, detail="Title bar height must be between 40 and 96."
        )
    if payload.title_bar_font_size < 12 or payload.title_bar_font_size > 40:
        raise HTTPException(
            status_code=400, detail="Title bar font size must be between 12 and 40."
        )

    backend_name = (
        get_config_value("llm", "backend", default=None) or "openai_compatible"
    ).strip().lower()
    if backend_name in {"koboldcpp", "kobold_cpp"}:
        set_config_value("llm", "koboldcpp", "base_url", value=model_url)
    else:
        set_config_value("llm", "openai_compatible", "base_url", value=model_url)

    set_config_value("llm", "max_tokens", value=payload.max_response_size)
    discussion_state.set_system_prompt(
        user_id=session.user_id,
        system_prompt=system_prompt,
        member_group_ids=set(),
    )
    set_config_value("ui", "theme", value=payload.theme)
    set_config_value("ui", "font_family", value=payload.font_family)
    set_config_value("ui", "font_size", value=payload.font_size)
    set_config_value("ui", "title_bar_height", value=payload.title_bar_height)
    set_config_value("ui", "title_bar_font_size", value=payload.title_bar_font_size)
    return {"status": "saved"}


@router.post("/users")
def api_create_user(request: Request, payload: CreateUserPayload):
    _require_session(request)
    try:
        user = create_user(username=payload.username, password=payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="User management not implemented yet.") from error
    return {"status": "created", "user": _serialize_user(user)}


@router.post("/users/verify")
def api_verify_user(request: Request, payload: VerifyUserPayload):
    _require_session(request)
    try:
        valid = verify_user(username=payload.username, password=payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="User management not implemented yet.") from error
    return {"valid": bool(valid)}


@router.patch("/users/{user_id}")
def api_edit_user(request: Request, user_id: int, payload: EditUserPayload):
    session = _require_session(request)
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="User access denied.")
    try:
        user = edit_user(
            user_id=user_id,
            username=payload.username,
            password=payload.password,
            is_enabled=payload.is_enabled,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="User management not implemented yet.") from error
    return {"status": "updated", "user": _serialize_user(user)}


@router.delete("/users/{user_id}")
def api_delete_user(request: Request, user_id: int):
    session = _require_session(request)
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="User access denied.")
    try:
        deleted = delete_user(user_id=user_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="User management not implemented yet.") from error
    return {"status": "deleted" if deleted else "not_found"}


@router.get("/users")
def api_list_users(request: Request):
    _require_session(request)
    try:
        users = list_users()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="User management not implemented yet.") from error
    return {"users": [_serialize_user(user) for user in users]}


@router.post("/groups")
def api_create_group(request: Request, payload: CreateGroupPayload):
    session = _require_session(request)
    try:
        group = create_group(
            name=payload.name,
            created_by_user_id=session.user_id,
            description=payload.description,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="Group management not implemented yet.") from error
    return {"status": "created", "group": _serialize_group(group)}


@router.delete("/groups/{group_id}")
def api_delete_group(request: Request, group_id: int):
    session = _require_session(request)
    if not _is_group_owner(group_id, session.user_id):
        raise HTTPException(status_code=403, detail="Group owner access required.")
    try:
        deleted = delete_group(group_id=group_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="Group management not implemented yet.") from error
    return {"status": "deleted" if deleted else "not_found"}


@router.get("/groups")
def api_list_groups(request: Request):
    session = _require_session(request)
    try:
        groups = list_groups()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="Group management not implemented yet.") from error
    memberships = list_user_groups(session.user_id)
    member_group_ids = {
        int(m["group_id"]) if isinstance(m, dict) else int(m.group_id)
        for m in memberships
        if (m.get("is_enabled", True) if isinstance(m, dict) else m.is_enabled)
    }
    visible_groups = []
    for group in groups:
        group_id = int(group["id"]) if isinstance(group, dict) else int(group.id or 0)
        if group_id in member_group_ids:
            visible_groups.append(group)

    return {"groups": [_serialize_group(group) for group in visible_groups]}


@router.post("/groups/{group_id}/members")
def api_add_member(request: Request, group_id: int, payload: AddMemberPayload):
    session = _require_session(request)
    if not _is_group_owner(group_id, session.user_id):
        raise HTTPException(status_code=403, detail="Group owner access required.")
    try:
        membership = add_member(group_id=group_id, user_id=payload.user_id, role=payload.role)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="Group management not implemented yet.") from error
    return {"status": "created", "membership": _serialize_membership(membership)}


@router.get("/auth/session")
def api_auth_session(request: Request):
    return _session_payload(request)


@router.post("/auth/register")
def api_auth_register(payload: AuthPayload, response: Response):
    try:
        user = register_user(username=payload.username, password=payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="User management not implemented yet.") from error

    session = login_user(payload.username, payload.password)
    if session is None:
        raise HTTPException(status_code=500, detail="Registration succeeded but login failed.")

    response.set_cookie(
        key="apmatia_session",
        value=session.token,
        httponly=True,
        samesite="lax",
    )
    return {"status": "registered", "user": _serialize_user(user)}


@router.post("/auth/login")
def api_auth_login(payload: AuthPayload, response: Response):
    try:
        session = login_user(username=payload.username, password=payload.password)
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="User management not implemented yet.") from error

    if session is None:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    response.set_cookie(
        key="apmatia_session",
        value=session.token,
        httponly=True,
        samesite="lax",
    )
    return {"status": "authenticated", "username": session.username}


@router.post("/auth/logout")
def api_auth_logout(request: Request, response: Response):
    token = request.cookies.get("apmatia_session")
    logout_session(token)
    response.delete_cookie("apmatia_session")
    return {"status": "logged_out"}
