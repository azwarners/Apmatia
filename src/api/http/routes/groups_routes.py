from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.api.internal.user_management import add_member, create_group, delete_group, list_group_members, list_groups
from src.api.internal.group_access import is_group_owner, visible_groups
from src.api.internal.user_management import GroupRole

from .shared import member_group_ids, require_session, serialize_group, serialize_membership

router = APIRouter()


class CreateGroupPayload(BaseModel):
    name: str
    created_by_user_id: int
    description: str = ""


class AddMemberPayload(BaseModel):
    user_id: int
    role: GroupRole = GroupRole.MEMBER


@router.post("/groups")
def api_create_group(request: Request, payload: CreateGroupPayload):
    session = require_session(request)
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
    return {"status": "created", "group": serialize_group(group)}


@router.delete("/groups/{group_id}")
def api_delete_group(request: Request, group_id: int):
    session = require_session(request)
    if not is_group_owner(list_group_members(group_id), session.user_id):
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
    session = require_session(request)
    try:
        groups = list_groups()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="Group management not implemented yet.") from error
    group_ids = member_group_ids(session.user_id)
    return {"groups": [serialize_group(group) for group in visible_groups(groups, group_ids)]}


@router.post("/groups/{group_id}/members")
def api_add_member(request: Request, group_id: int, payload: AddMemberPayload):
    session = require_session(request)
    if not is_group_owner(list_group_members(group_id), session.user_id):
        raise HTTPException(status_code=403, detail="Group owner access required.")
    try:
        membership = add_member(group_id=group_id, user_id=payload.user_id, role=payload.role)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="Group management not implemented yet.") from error
    return {"status": "created", "membership": serialize_membership(membership)}
