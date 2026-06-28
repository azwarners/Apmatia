from __future__ import annotations

import os

from src.core.app_config import get_config_value, set_config_value


def get_settings_payload() -> dict:
    llama_server_log_dir = get_config_value("llama_server", "log_dir", default=None)
    if not llama_server_log_dir:
        llama_server_log_dir = (
            os.getenv("APMATIA_LLAMA_SERVER_LOG_DIR")
            or os.getenv("LLAMA_LOG_DIR")
            or ""
        )
    theme = get_config_value("ui", "theme", default="dark")
    font_family = get_config_value("ui", "font_family", default="system-ui")
    font_size = get_config_value("ui", "font_size", default=16)
    title_bar_height = get_config_value("ui", "title_bar_height", default=56)
    title_bar_font_size = get_config_value("ui", "title_bar_font_size", default=20)
    return {
        "llama_server_log_dir": str(llama_server_log_dir or ""),
        "theme": str(theme or "dark"),
        "font_family": str(font_family or "system-ui"),
        "font_size": int(font_size),
        "title_bar_height": int(title_bar_height),
        "title_bar_font_size": int(title_bar_font_size),
    }


def save_settings_payload(
    *,
    llama_server_log_dir: str,
    theme: str,
    font_family: str,
    font_size: int,
    title_bar_height: int,
    title_bar_font_size: int,
) -> None:
    clean_llama_server_log_dir = llama_server_log_dir.strip()
    if theme not in {"system", "dark", "light"}:
        raise ValueError("Theme must be 'system', 'dark', or 'light'.")
    if font_size < 12 or font_size > 24:
        raise ValueError("Font size must be between 12 and 24.")
    if title_bar_height < 40 or title_bar_height > 96:
        raise ValueError("Title bar height must be between 40 and 96.")
    if title_bar_font_size < 12 or title_bar_font_size > 40:
        raise ValueError("Title bar font size must be between 12 and 40.")

    set_config_value("llama_server", "log_dir", value=clean_llama_server_log_dir)
    set_config_value("ui", "theme", value=theme)
    set_config_value("ui", "font_family", value=font_family)
    set_config_value("ui", "font_size", value=font_size)
    set_config_value("ui", "title_bar_height", value=title_bar_height)
    set_config_value("ui", "title_bar_font_size", value=title_bar_font_size)
