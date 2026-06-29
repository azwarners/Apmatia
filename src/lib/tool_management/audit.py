from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_AUDIT_LOCK = threading.Lock()


def _data_dir() -> Path:
    return Path(
        os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
    ).expanduser()


def _audit_path() -> Path:
    return _data_dir() / "tool_calls.jsonl"


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        return sorted(value)
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


def record_tool_call_event(payload: dict[str, Any]) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    path = _audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=True, sort_keys=True, default=_json_default)
    with _AUDIT_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
