from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.api.internal.user_management import create_user, delete_user, edit_user, list_users, verify_user

from .shared import require_session, serialize_user

router = APIRouter()


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


@router.post("/users")
def api_create_user(request: Request, payload: CreateUserPayload):
    require_session(request)
    try:
        user = create_user(username=payload.username, password=payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="User management not implemented yet.") from error
    return {"status": "created", "user": serialize_user(user)}


@router.post("/users/verify")
def api_verify_user(request: Request, payload: VerifyUserPayload):
    require_session(request)
    try:
        valid = verify_user(username=payload.username, password=payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="User management not implemented yet.") from error
    return {"valid": bool(valid)}


@router.patch("/users/{user_id}")
def api_edit_user(request: Request, user_id: int, payload: EditUserPayload):
    session = require_session(request)
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
    return {"status": "updated", "user": serialize_user(user)}


@router.delete("/users/{user_id}")
def api_delete_user(request: Request, user_id: int):
    session = require_session(request)
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
    require_session(request)
    try:
        users = list_users()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail="User management not implemented yet.") from error
    return {"users": [serialize_user(user) for user in users]}
