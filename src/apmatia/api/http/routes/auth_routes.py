from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from apmatia.api.internal.auth import login_user, logout_session, register_user

from .shared import serialize_user, session_payload

router = APIRouter()
AUTH_SESSION_COOKIE_NAME = "apmatia_session"
AUTH_SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


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
        key=AUTH_SESSION_COOKIE_NAME,
        value=session.token,
        httponly=True,
        samesite="lax",
        max_age=AUTH_SESSION_COOKIE_MAX_AGE_SECONDS,
        path="/",
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
        key=AUTH_SESSION_COOKIE_NAME,
        value=session.token,
        httponly=True,
        samesite="lax",
        max_age=AUTH_SESSION_COOKIE_MAX_AGE_SECONDS,
        path="/",
    )
    return {"status": "authenticated", "username": session.username}


@router.post("/auth/logout")
def api_auth_logout(request: Request, response: Response):
    token = request.cookies.get(AUTH_SESSION_COOKIE_NAME)
    logout_session(token)
    response.delete_cookie(AUTH_SESSION_COOKIE_NAME, path="/")
    return {"status": "logged_out"}
