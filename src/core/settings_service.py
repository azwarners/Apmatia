from __future__ import annotations

from src.core.app_config import get_config_value, set_config_value
from src.core.discussions import discussion_state


def get_settings_payload() -> dict:
    backend_name = (
        get_config_value("llm", "backend", default=None) or "openai_compatible"
    ).strip().lower()
    if backend_name in {"koboldcpp", "kobold_cpp"}:
        model_url = get_config_value("llm", "koboldcpp", "base_url", default=None)
    else:
        model_url = get_config_value(
            "llm", "openai_compatible", "base_url", default=None
        )

    max_tokens = get_config_value("llm", "max_tokens", default=8192)
    system_prompt = get_config_value("discussion", "system_prompt", default="")
    theme = get_config_value("ui", "theme", default="dark")
    font_family = get_config_value("ui", "font_family", default="system-ui")
    font_size = get_config_value("ui", "font_size", default=16)
    title_bar_height = get_config_value("ui", "title_bar_height", default=56)
    title_bar_font_size = get_config_value("ui", "title_bar_font_size", default=20)
    return {
        "backend": backend_name,
        "model_url": str(model_url or ""),
        "max_response_size": int(max_tokens),
        "system_prompt": str(system_prompt or ""),
        "theme": str(theme or "dark"),
        "font_family": str(font_family or "system-ui"),
        "font_size": int(font_size),
        "title_bar_height": int(title_bar_height),
        "title_bar_font_size": int(title_bar_font_size),
    }


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
    clean_model_url = model_url.strip()
    if not clean_model_url:
        raise ValueError("Model URL cannot be empty.")
    if max_response_size < 1:
        raise ValueError("Max response size must be at least 1.")
    if theme not in {"dark", "light"}:
        raise ValueError("Theme must be 'dark' or 'light'.")
    if font_size < 12 or font_size > 24:
        raise ValueError("Font size must be between 12 and 24.")
    if title_bar_height < 40 or title_bar_height > 96:
        raise ValueError("Title bar height must be between 40 and 96.")
    if title_bar_font_size < 12 or title_bar_font_size > 40:
        raise ValueError("Title bar font size must be between 12 and 40.")

    backend_name = (
        get_config_value("llm", "backend", default=None) or "openai_compatible"
    ).strip().lower()
    if backend_name in {"koboldcpp", "kobold_cpp"}:
        set_config_value("llm", "koboldcpp", "base_url", value=clean_model_url)
    else:
        set_config_value("llm", "openai_compatible", "base_url", value=clean_model_url)

    set_config_value("llm", "max_tokens", value=max_response_size)
    discussion_state.set_system_prompt(
        user_id=user_id,
        system_prompt=system_prompt,
        member_group_ids=set(),
    )
    set_config_value("ui", "theme", value=theme)
    set_config_value("ui", "font_family", value=font_family)
    set_config_value("ui", "font_size", value=font_size)
    set_config_value("ui", "title_bar_height", value=title_bar_height)
    set_config_value("ui", "title_bar_font_size", value=title_bar_font_size)
