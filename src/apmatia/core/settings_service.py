from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apmatia.core.app_config import get_config_value, set_config_value
from apmatia.core.runtime_paths import get_app_dir


DEFAULT_ACCENT_COLOR = "#ff6b6b"
DEFAULT_TERMINAL_BACKGROUND_COLOR = "#000000"
DEFAULT_TERMINAL_TEXT_COLOR = "#9dffad"
DEFAULT_TERMINAL_BORDER_COLOR = "rgba(110, 255, 170, 0.35)"
DEFAULT_TERMINAL_MUTED_COLOR = "rgba(157, 255, 173, 0.72)"
DEFAULT_TIMEZONE = "America/Phoenix"
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
    gguf_directories = _get_gguf_directories()
    auto_scan_gguf_directory = bool(get_config_value("ai_model_manager", "auto_scan_gguf_directory", default=True))
    llama_server_executable_path = get_config_value("ai_model_executor", "runtime_config", "executable_path", default=None)
    if not llama_server_executable_path:
        llama_server_executable_path = os.getenv("APMATIA_LLAMA_SERVER_EXECUTABLE_PATH") or "llama-server"
    llama_server_default_args = _join_args(get_config_value("ai_model_executor", "runtime_config", "default_args", default=[]))
    if not llama_server_default_args:
        llama_server_default_args = _join_args(os.getenv("APMATIA_LLAMA_SERVER_DEFAULT_ARGS") or "")
    workspace_root = _ensure_directory(
        get_config_value("workspace", "root", default=None) or os.getenv("APMATIA_WORKSPACE_ROOT"),
        default=get_app_dir() / "workspace",
    )
    knowledge_root = _ensure_directory(
        get_config_value("knowledge", "root", default=None) or os.getenv("APMATIA_KNOWLEDGE_ROOT"),
        default=get_app_dir() / "knowledge",
    )
    timezone_name = _normalize_timezone_name(
        get_config_value("ui", "timezone", default=None) or os.getenv("APMATIA_TIMEZONE"),
    )
    theme = get_config_value("ui", "theme", default="dark")
    font_family = get_config_value("ui", "font_family", default="system-ui")
    accent_color = _normalize_hex_color(get_config_value("ui", "accent_color", default=DEFAULT_ACCENT_COLOR))
    font_size = get_config_value("ui", "font_size", default=16)
    title_bar_height = get_config_value("ui", "title_bar_height", default=56)
    title_bar_font_size = get_config_value("ui", "title_bar_font_size", default=20)
    terminal_background_color = _normalize_hex_color(
        get_config_value("ui", "terminal_background_color", default=DEFAULT_TERMINAL_BACKGROUND_COLOR),
        default=DEFAULT_TERMINAL_BACKGROUND_COLOR,
    )
    terminal_text_color = _normalize_hex_color(
        get_config_value("ui", "terminal_text_color", default=DEFAULT_TERMINAL_TEXT_COLOR),
        default=DEFAULT_TERMINAL_TEXT_COLOR,
    )
    terminal_border_color = str(
        get_config_value("ui", "terminal_border_color", default=DEFAULT_TERMINAL_BORDER_COLOR) or DEFAULT_TERMINAL_BORDER_COLOR
    )
    terminal_muted_color = str(
        get_config_value("ui", "terminal_muted_color", default=DEFAULT_TERMINAL_MUTED_COLOR) or DEFAULT_TERMINAL_MUTED_COLOR
    )
    return {
        "llama_server_log_dir": str(llama_server_log_dir or ""),
        "gguf_directories": _join_directories(gguf_directories),
        "gguf_directory": gguf_directories[0] if gguf_directories else "",
        "auto_scan_gguf_directory": auto_scan_gguf_directory,
        "llama_server_executable_path": str(llama_server_executable_path or "llama-server"),
        "llama_server_default_args": llama_server_default_args,
        "workspace_root": str(workspace_root),
        "knowledge_root": str(knowledge_root),
        "timezone": timezone_name,
        "theme": str(theme or "dark"),
        "font_family": str(font_family or "system-ui"),
        "accent_color": accent_color,
        "font_size": int(font_size),
        "title_bar_height": int(title_bar_height),
        "title_bar_font_size": int(title_bar_font_size),
        "terminal_background_color": terminal_background_color,
        "terminal_text_color": terminal_text_color,
        "terminal_border_color": terminal_border_color,
        "terminal_muted_color": terminal_muted_color,
    }


def save_settings_payload(
    *,
    llama_server_log_dir: str,
    gguf_directories: str,
    auto_scan_gguf_directory: bool,
    llama_server_executable_path: str,
    llama_server_default_args: str,
    workspace_root: str,
    knowledge_root: str,
    timezone: str,
    theme: str,
    font_family: str,
    accent_color: str,
    font_size: int,
    title_bar_height: int,
    title_bar_font_size: int,
    terminal_background_color: str = DEFAULT_TERMINAL_BACKGROUND_COLOR,
    terminal_text_color: str = DEFAULT_TERMINAL_TEXT_COLOR,
    terminal_border_color: str = DEFAULT_TERMINAL_BORDER_COLOR,
    terminal_muted_color: str = DEFAULT_TERMINAL_MUTED_COLOR,
) -> None:
    clean_llama_server_log_dir = llama_server_log_dir.strip()
    clean_gguf_directories = _split_directories(gguf_directories)
    clean_gguf_directory = clean_gguf_directories[0] if clean_gguf_directories else ""
    clean_llama_server_executable_path = llama_server_executable_path.strip() or "llama-server"
    clean_llama_server_default_args = [part.strip() for part in llama_server_default_args.splitlines() if part.strip()]
    clean_accent_color = _normalize_hex_color(accent_color)
    clean_terminal_background_color = _normalize_hex_color(
        terminal_background_color,
        default=DEFAULT_TERMINAL_BACKGROUND_COLOR,
    )
    clean_terminal_text_color = _normalize_hex_color(
        terminal_text_color,
        default=DEFAULT_TERMINAL_TEXT_COLOR,
    )
    clean_terminal_border_color = str(terminal_border_color).strip() or DEFAULT_TERMINAL_BORDER_COLOR
    clean_terminal_muted_color = str(terminal_muted_color).strip() or DEFAULT_TERMINAL_MUTED_COLOR
    clean_timezone = _normalize_timezone_name(timezone, strict=True)
    if theme not in {"system", "dark", "light"}:
        raise ValueError("Theme must be 'system', 'dark', or 'light'.")
    if clean_accent_color != accent_color.strip().lower():
        raise ValueError("Accent color must be a valid hex color like #ff6b6b.")
    if clean_terminal_background_color != terminal_background_color.strip().lower():
        raise ValueError("Terminal background color must be a valid hex color like #000000.")
    if clean_terminal_text_color != terminal_text_color.strip().lower():
        raise ValueError("Terminal text color must be a valid hex color like #9dffad.")
    if font_size < 12 or font_size > 24:
        raise ValueError("Font size must be between 12 and 24.")
    if title_bar_height < 40 or title_bar_height > 96:
        raise ValueError("Title bar height must be between 40 and 96.")
    if title_bar_font_size < 12 or title_bar_font_size > 40:
        raise ValueError("Title bar font size must be between 12 and 40.")

    clean_workspace_root = _ensure_directory(workspace_root, default=get_app_dir() / "workspace")
    clean_knowledge_root = _ensure_directory(knowledge_root, default=get_app_dir() / "knowledge")

    set_config_value("llama_server", "log_dir", value=clean_llama_server_log_dir)
    set_config_value("workspace", "root", value=str(clean_workspace_root))
    set_config_value("knowledge", "root", value=str(clean_knowledge_root))
    set_config_value("ui", "timezone", value=clean_timezone)
    set_config_value("ai_model_manager", "gguf_directories", value=clean_gguf_directories)
    set_config_value("ai_model_manager", "gguf_directory", value=clean_gguf_directory)
    set_config_value("ai_model_manager", "auto_scan_gguf_directory", value=bool(auto_scan_gguf_directory))
    set_config_value("ai_model_executor", "runtime_config", "executable_path", value=clean_llama_server_executable_path)
    set_config_value("ai_model_executor", "runtime_config", "default_args", value=clean_llama_server_default_args)
    set_config_value("ui", "theme", value=theme)
    set_config_value("ui", "font_family", value=font_family)
    set_config_value("ui", "accent_color", value=clean_accent_color)
    set_config_value("ui", "font_size", value=font_size)
    set_config_value("ui", "title_bar_height", value=title_bar_height)
    set_config_value("ui", "title_bar_font_size", value=title_bar_font_size)
    set_config_value("ui", "terminal_background_color", value=clean_terminal_background_color)
    set_config_value("ui", "terminal_text_color", value=clean_terminal_text_color)
    set_config_value("ui", "terminal_border_color", value=clean_terminal_border_color)
    set_config_value("ui", "terminal_muted_color", value=clean_terminal_muted_color)

    if clean_gguf_directories:
        from apmatia.modules.ai_model_manager import AIModelManager

        manager = AIModelManager()
        for directory in clean_gguf_directories:
            gguf_path = Path(directory).expanduser()
            if not gguf_path.exists() or not gguf_path.is_dir():
                continue
            manager.scan_gguf_directory(gguf_path, recursive=True)


def _ensure_directory(value: object, *, default: Path) -> Path:
    raw_value = str(value or "").strip()
    path = Path(raw_value).expanduser() if raw_value else default.expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_timezone_name(value: object, *, default: str = DEFAULT_TIMEZONE, strict: bool = False) -> str:
    timezone_name = str(value or "").strip()
    if not timezone_name:
        return default
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        if not strict:
            return default
        raise ValueError(
            "Timezone must be a valid IANA timezone like America/Phoenix."
        ) from error
    return timezone_name


def resolve_timezone_name() -> str:
    return _normalize_timezone_name(get_config_value("ui", "timezone", default=None) or os.getenv("APMATIA_TIMEZONE"))


def resolve_timezone() -> ZoneInfo:
    return ZoneInfo(resolve_timezone_name())


def _get_gguf_directories() -> list[str]:
    directories = get_config_value("ai_model_manager", "gguf_directories", default=None)
    if isinstance(directories, (list, tuple)):
        cleaned = [str(item).strip() for item in directories if str(item).strip()]
        if cleaned:
            return cleaned

    legacy_directory = get_config_value("ai_model_manager", "gguf_directory", default=None)
    if legacy_directory:
        cleaned = str(legacy_directory).strip()
        if cleaned:
            return [cleaned]

    env_directories = os.getenv("APMATIA_GGUF_DIRECTORIES") or ""
    if env_directories.strip():
        return _split_directories(env_directories)

    legacy_env = os.getenv("APMATIA_GGUF_DIRECTORY") or ""
    if legacy_env.strip():
        return [legacy_env.strip()]

    return []


def _split_directories(value: str) -> list[str]:
    if not value.strip():
        return []
    normalized = value.replace(os.pathsep, "\n").replace(",", "\n")
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def _join_directories(values: list[str]) -> str:
    return "\n".join(value.strip() for value in values if str(value).strip())


def _join_args(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    return str(value)
