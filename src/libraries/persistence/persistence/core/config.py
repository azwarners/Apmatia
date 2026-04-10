from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _is_yaml_path(path: Path) -> bool:
    return path.suffix.lower() in {".yaml", ".yml"}


def _read_yaml(path: Path) -> Any:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load YAML config files.") from exc

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to save YAML config files.") from exc

    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            data,
            file,
            default_flow_style=False,
            indent=2,
            sort_keys=False,
            allow_unicode=True,
        )


def load_config_file(path: str | Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    config_path = Path(path).expanduser()
    fallback = default or {}

    if not config_path.exists():
        return fallback

    try:
        if _is_yaml_path(config_path):
            loaded = _read_yaml(config_path)
        else:
            with config_path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
    except Exception:
        return fallback

    return loaded if isinstance(loaded, dict) else fallback


def save_config_file(path: str | Path, data: dict[str, Any]) -> None:
    config_path = Path(path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if _is_yaml_path(config_path):
        _write_yaml(config_path, data)
        return

    with config_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
