from __future__ import annotations

import os
import re

from src.core.app_config import get_config_value, set_config_value


DEFAULT_ACCENT_COLOR = "#ff6b6b"
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _normalize_hex_color(value: object, *, default: str = DEFAULT_ACCENT_COLOR) -> str:
    color = str(value or "").strip()
    if not color:
        return default
    if not _HEX_COLOR_RE.fullmatch(color):
        return default
    return color.lower()


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
    accent_color = _normalize_hex_color(get_config_value("ui", "accent_color", default=DEFAULT_ACCENT_COLOR))
    font_size = get_config_value("ui", "font_size", default=16)
    title_bar_height = get_config_value("ui", "title_bar_height", default=56)
    title_bar_font_size = get_config_value("ui", "title_bar_font_size", default=20)
    return {
        "llama_server_log_dir": str(llama_server_log_dir or ""),
        "theme": str(theme or "dark"),
        "font_family": str(font_family or "system-ui"),
        "accent_color": accent_color,
        "font_size": int(font_size),
        "title_bar_height": int(title_bar_height),
        "title_bar_font_size": int(title_bar_font_size),
    }


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
    clean_llama_server_log_dir = llama_server_log_dir.strip()
    clean_accent_color = _normalize_hex_color(accent_color)
    if theme not in {"system", "dark", "light"}:
        raise ValueError("Theme must be 'system', 'dark', or 'light'.")
    if clean_accent_color != accent_color.strip().lower():
        raise ValueError("Accent color must be a valid hex color like #ff6b6b.")
    if font_size < 12 or font_size > 24:
        raise ValueError("Font size must be between 12 and 24.")
    if title_bar_height < 40 or title_bar_height > 96:
        raise ValueError("Title bar height must be between 40 and 96.")
    if title_bar_font_size < 12 or title_bar_font_size > 40:
        raise ValueError("Title bar font size must be between 12 and 40.")

    set_config_value("llama_server", "log_dir", value=clean_llama_server_log_dir)
    set_config_value("ui", "theme", value=theme)
    set_config_value("ui", "font_family", value=font_family)
    set_config_value("ui", "accent_color", value=clean_accent_color)
    set_config_value("ui", "font_size", value=font_size)
    set_config_value("ui", "title_bar_height", value=title_bar_height)
    set_config_value("ui", "title_bar_font_size", value=title_bar_font_size)
