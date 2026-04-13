from __future__ import annotations

from src.core.settings_service import (
    get_settings_payload as _get_settings_payload,
    save_settings_payload as _save_settings_payload,
)


def get_settings_payload() -> dict:
    return _get_settings_payload()


def save_settings_payload(*,
    user_id: int,
    model_url: str,
    max_response_size: int,
    system_prompt: str,
    theme: str,
    font_family: str,
    font_size: int,
    title_bar_height: int,
    title_bar_font_size: int,
) -> None:
    _save_settings_payload(
        user_id=user_id,
        model_url=model_url,
        max_response_size=max_response_size,
        system_prompt=system_prompt,
        theme=theme,
        font_family=font_family,
        font_size=font_size,
        title_bar_height=title_bar_height,
        title_bar_font_size=title_bar_font_size,
    )
