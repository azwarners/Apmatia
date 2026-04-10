from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from src.core.config_persistence import load_config_file, save_config_file


PREFERRED_CONFIG_DIR = Path.home() / ".config" / "apmatia"
LEGACY_APP_DIR = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
LEGACY_STATE_FILE = LEGACY_APP_DIR / "state.json"


def _resolve_config_dir() -> Path:
    env_override = os.getenv("APMATIA_CONFIG_DIR")
    if env_override:
        return Path(env_override).expanduser()

    preferred = PREFERRED_CONFIG_DIR
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "apmatia"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _config_file() -> Path:
    return _resolve_config_dir() / "config.json"


def _default_config() -> dict[str, Any]:
    return {
        "llm": {
            "model_name": "default",
            "max_tokens": 8192,
            "backend": "openai_compatible",
            "openai_compatible": {
                "base_url": "http://localhost:5001",
                "api_key": None,
                "model_name": None,
            },
            "koboldcpp": {
                "base_url": "http://localhost:5001",
            },
        },
        "discussion": {
            "current_discussion_id": None,
            "system_prompt": "",
        },
        "ui": {
            "theme": "dark",
            "font_family": "system-ui",
            "font_size": 16,
        },
    }


def _merge_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _set_nested(config: dict[str, Any], keys: tuple[str, ...], value: Any) -> None:
    current = config
    for key in keys[:-1]:
        if not isinstance(current.get(key), dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _seed_from_env(config: dict[str, Any]) -> dict[str, Any]:
    env_map: dict[str, tuple[str, ...]] = {
        "LLM_MODEL": ("llm", "model_name"),
        "LLM_MAX_TOKENS": ("llm", "max_tokens"),
        "YSPARR_TEXT2TEXT_BACKEND": ("llm", "backend"),
        "OPENAI_COMPAT_BASE_URL": ("llm", "openai_compatible", "base_url"),
        "OPENAI_COMPAT_API_KEY": ("llm", "openai_compatible", "api_key"),
        "OPENAI_COMPAT_MODEL": ("llm", "openai_compatible", "model_name"),
        "KOBOLDCPP_URL": ("llm", "koboldcpp", "base_url"),
    }

    seeded = dict(config)
    for env_key, cfg_keys in env_map.items():
        env_value = os.getenv(env_key)
        if env_value is None or env_value == "":
            continue

        if env_key == "LLM_MAX_TOKENS":
            try:
                _set_nested(seeded, cfg_keys, int(env_value))
            except ValueError:
                continue
        else:
            _set_nested(seeded, cfg_keys, env_value)
    return seeded


def _migrate_legacy_state(config: dict[str, Any]) -> dict[str, Any]:
    if not LEGACY_STATE_FILE.exists():
        return config

    try:
        legacy_data = load_config_file(LEGACY_STATE_FILE, default={})
    except Exception:
        return config

    if not isinstance(legacy_data, dict):
        return config

    migrated = dict(config)
    current_discussion_id = legacy_data.get("current_discussion_id")
    system_prompt = legacy_data.get("system_prompt")

    discussion = dict(migrated.get("discussion", {}))
    if current_discussion_id and not discussion.get("current_discussion_id"):
        discussion["current_discussion_id"] = str(current_discussion_id)
    if isinstance(system_prompt, str) and not discussion.get("system_prompt"):
        discussion["system_prompt"] = system_prompt

    migrated["discussion"] = discussion
    return migrated


def load_app_config() -> dict[str, Any]:
    config_file = _config_file()
    loaded = load_config_file(config_file, default={})
    config = loaded if isinstance(loaded, dict) else {}
    merged = _merge_dicts(_default_config(), config)
    migrated = _migrate_legacy_state(merged)
    seeded = _seed_from_env(migrated)
    if seeded != config:
        save_app_config(seeded)
    return seeded


def save_app_config(config: dict[str, Any]) -> None:
    save_config_file(_config_file(), config)


def get_config_value(*keys: str, default: Any = None) -> Any:
    config = load_app_config()
    current: Any = config
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def set_config_value(*keys: str, value: Any) -> dict[str, Any]:
    if not keys:
        raise ValueError("At least one key is required")

    config = load_app_config()
    _set_nested(config, tuple(keys), value)
    save_app_config(config)
    return config
