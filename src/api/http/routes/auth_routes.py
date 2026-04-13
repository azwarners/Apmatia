from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from src.api.internal.auth import login_user, logout_session, register_user

from .shared import serialize_user, session_payload

router = APIRouter()


class AuthPayload(BaseModel):
    username: str
    password: str


@router.get("/auth/session")
def api_auth_session(request: Request):
    return session_payload(request)


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
    return {"status": "registered", "user": serialize_user(user)}


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
