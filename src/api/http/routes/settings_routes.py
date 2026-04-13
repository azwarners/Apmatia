from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.api.internal.settings import get_settings_payload, save_settings_payload

from .shared import require_session

router = APIRouter()


class SettingsPayload(BaseModel):
    model_url: str
    max_response_size: int
    system_prompt: str
    theme: str = "dark"
    font_family: str = "system-ui"
    font_size: int = 16
    title_bar_height: int = 56
    title_bar_font_size: int = 20


@router.get("/settings")
def get_settings(request: Request):
    require_session(request)
    return get_settings_payload()


@router.post("/settings")
def save_settings(request: Request, payload: SettingsPayload):
    session = require_session(request)
    try:
        save_settings_payload(
            user_id=session.user_id,
            model_url=payload.model_url,
            max_response_size=payload.max_response_size,
            system_prompt=payload.system_prompt,
            theme=payload.theme,
            font_family=payload.font_family,
            font_size=payload.font_size,
            title_bar_height=payload.title_bar_height,
            title_bar_font_size=payload.title_bar_font_size,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "saved"}
