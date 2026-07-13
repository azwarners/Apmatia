from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from apmatia.api.internal.settings import get_settings_payload, save_settings_payload

from .shared import require_session

router = APIRouter()


class SettingsPayload(BaseModel):
    llama_server_log_dir: str = ""
    gguf_directories: str = ""
    gguf_directory: str = ""
    auto_scan_gguf_directory: bool = True
    llama_server_executable_path: str = "llama-server"
    llama_server_default_args: str = ""
    theme: str = "dark"
    font_family: str = "system-ui"
    accent_color: str = "#ff6b6b"
    font_size: int = 16
    title_bar_height: int = 56
    title_bar_font_size: int = 20
    terminal_background_color: str = "#000000"
    terminal_text_color: str = "#9dffad"
    terminal_border_color: str = "rgba(110, 255, 170, 0.35)"
    terminal_muted_color: str = "rgba(157, 255, 173, 0.72)"


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
            gguf_directories=payload.gguf_directories or payload.gguf_directory,
            auto_scan_gguf_directory=payload.auto_scan_gguf_directory,
            llama_server_executable_path=payload.llama_server_executable_path,
            llama_server_default_args=payload.llama_server_default_args,
            theme=payload.theme,
            font_family=payload.font_family,
            accent_color=payload.accent_color,
            font_size=payload.font_size,
            title_bar_height=payload.title_bar_height,
            title_bar_font_size=payload.title_bar_font_size,
            terminal_background_color=payload.terminal_background_color,
            terminal_text_color=payload.terminal_text_color,
            terminal_border_color=payload.terminal_border_color,
            terminal_muted_color=payload.terminal_muted_color,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "saved"}
