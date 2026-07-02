from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from apmatia.api.internal.settings import get_settings_payload, save_settings_payload

from .shared import require_session

router = APIRouter()


class SettingsPayload(BaseModel):
    llama_server_log_dir: str = ""
    theme: str = "dark"
    font_family: str = "system-ui"
    accent_color: str = "#ff6b6b"
    font_size: int = 16
    title_bar_height: int = 56
    title_bar_font_size: int = 20


@router.get("/settings")
def get_settings(request: Request):
    require_session(request)
    return get_settings_payload()


@router.post("/settings")
def save_settings(request: Request, payload: SettingsPayload):
    require_session(request)
    try:
        save_settings_payload(
            llama_server_log_dir=payload.llama_server_log_dir,
            theme=payload.theme,
            font_family=payload.font_family,
            accent_color=payload.accent_color,
            font_size=payload.font_size,
            title_bar_height=payload.title_bar_height,
            title_bar_font_size=payload.title_bar_font_size,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "saved"}
