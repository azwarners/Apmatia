from __future__ import annotations

from apmatia.core.settings_service import (
    get_settings_payload as _get_settings_payload,
    save_settings_payload as _save_settings_payload,
)


def get_settings_payload() -> dict:
    return _get_settings_payload()


def save_settings_payload(
    *,
    llama_server_log_dir: str,
    theme: str,
    font_family: str,
    accent_color: str,
    font_size: int,
    title_bar_height: int,
    title_bar_font_size: int,
) -> None:
    _save_settings_payload(
        llama_server_log_dir=llama_server_log_dir,
        theme=theme,
        font_family=font_family,
        accent_color=accent_color,
        font_size=font_size,
        title_bar_height=title_bar_height,
        title_bar_font_size=title_bar_font_size,
    )
