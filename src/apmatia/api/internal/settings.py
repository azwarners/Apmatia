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
    gguf_directories: str,
    auto_scan_gguf_directory: bool,
    llama_server_executable_path: str,
    llama_server_default_args: str,
    theme: str,
    font_family: str,
    accent_color: str,
    font_size: int,
    title_bar_height: int,
    title_bar_font_size: int,
) -> None:
    _save_settings_payload(
        llama_server_log_dir=llama_server_log_dir,
        gguf_directories=gguf_directories,
        auto_scan_gguf_directory=auto_scan_gguf_directory,
        llama_server_executable_path=llama_server_executable_path,
        llama_server_default_args=llama_server_default_args,
        theme=theme,
        font_family=font_family,
        accent_color=accent_color,
        font_size=font_size,
        title_bar_height=title_bar_height,
        title_bar_font_size=title_bar_font_size,
    )
