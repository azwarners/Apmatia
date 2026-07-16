from __future__ import annotations

import json
import logging
import os
import re
from collections import deque
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Any

from apmatia.core.runtime_paths import get_app_dir


_LOGGER_NAME = "apmatia"
_FILE_HANDLER_MARKER = "_apmatia_file_handler"
_STREAM_HANDLER_MARKER = "_apmatia_stream_handler"
_CONFIGURED_MARKER = "_apmatia_logging_configured"
_AGENT_LOOP_HANDLER_MARKER = "_apmatia_agent_loop_handler"
_AGENT_LOOP_LOGGER_NAME = "apmatia.agent_loop"
_DEFAULT_LOG_BASENAME = "apmatia.jsonl"
_AGENT_LOOP_LOG_DIR_NAME = "agent_loop"
_DEFAULT_TAIL_LIMIT = 200
_NOISY_LOGGER_LEVELS = {
    "watchdog": logging.WARNING,
}


def get_log_dir() -> Path:
    override = os.getenv("APMATIA_LOG_DIR")
    if override:
        return Path(override).expanduser()
    return get_app_dir() / "logs"


def get_log_file_path() -> Path:
    override = os.getenv("APMATIA_LOG_FILE")
    if override:
        return Path(override).expanduser()
    return get_log_dir() / _DEFAULT_LOG_BASENAME


def get_agent_loop_log_dir() -> Path:
    return get_log_dir() / _AGENT_LOOP_LOG_DIR_NAME


def get_agent_loop_log_path(task_id: str | None = None) -> Path:
    if task_id is None or not str(task_id).strip():
        return get_agent_loop_log_dir() / "agent_loop.jsonl"
    return get_agent_loop_log_dir() / f"{_sanitize_log_stem(str(task_id))}.jsonl"


def configure_logging() -> logging.Logger:
    root_logger = logging.getLogger()
    if getattr(root_logger, _CONFIGURED_MARKER, False):
        return logging.getLogger(_LOGGER_NAME)

    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = get_log_file_path()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger.setLevel(logging.DEBUG)

    file_handler = _build_file_handler(log_file)
    stream_handler = _build_stream_handler()

    _remove_apmatia_handlers(root_logger)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    _set_logger_levels(_NOISY_LOGGER_LEVELS)
    setattr(root_logger, _CONFIGURED_MARKER, True)
    logging.captureWarnings(True)

    return logging.getLogger(_LOGGER_NAME)


def configure_agent_loop_logging() -> logging.Logger:
    logger = logging.getLogger(_AGENT_LOOP_LOGGER_NAME)
    log_dir = get_agent_loop_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    existing_handlers = [handler for handler in logger.handlers if getattr(handler, _AGENT_LOOP_HANDLER_MARKER, False)]
    for handler in existing_handlers:
        if getattr(handler, "_log_dir", None) == log_dir:
            logger.setLevel(logging.DEBUG)
            logger.propagate = False
            return logger
        logger.removeHandler(handler)

    handler = _AgentLoopFileHandler(log_dir)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False
    setattr(logger, _AGENT_LOOP_HANDLER_MARKER, True)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    configure_logging()
    normalized_name = str(name or _LOGGER_NAME).strip() or _LOGGER_NAME
    return logging.getLogger(normalized_name)


def get_agent_loop_logger(name: str | None = None) -> logging.Logger:
    configure_agent_loop_logging()
    normalized_name = str(name or _AGENT_LOOP_LOGGER_NAME).strip() or _AGENT_LOOP_LOGGER_NAME
    return logging.getLogger(normalized_name)


def read_structured_log_entries(
    *,
    limit: int = _DEFAULT_TAIL_LIMIT,
    include_agent_loop_logs: bool = False,
) -> list[dict[str, Any]]:
    log_files: list[tuple[Path, str]] = [(get_log_file_path(), "app")]
    if include_agent_loop_logs:
        agent_loop_dir = get_agent_loop_log_dir()
        if agent_loop_dir.exists():
            for path in sorted(agent_loop_dir.glob("*.jsonl")):
                log_files.append((path, f"agent_loop/{path.stem}"))

    entries: list[dict[str, Any]] = []
    for log_file, source in log_files:
        if not log_file.exists():
            continue
        entries.extend(_read_structured_log_entries_from_file(log_file, source=source))

    if limit <= 0 or not entries:
        return []

    entries.sort(key=_log_entry_sort_key)
    if len(entries) > limit:
        entries = entries[-limit:]
    return entries


def read_agent_loop_log_entries(*, limit: int = _DEFAULT_TAIL_LIMIT) -> list[dict[str, Any]]:
    return read_structured_log_entries(limit=limit, include_agent_loop_logs=True)


def clear_log_file() -> None:
    log_file = get_log_file_path()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("", encoding="utf-8")


def clear_agent_loop_log_dir() -> None:
    log_dir = get_agent_loop_log_dir()
    if not log_dir.exists():
        return
    for path in log_dir.glob("*.jsonl"):
        path.unlink(missing_ok=True)


def _build_file_handler(log_file: Path) -> logging.Handler:
    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(_JsonLogFormatter())
    setattr(handler, _FILE_HANDLER_MARKER, True)
    return handler


def _build_stream_handler() -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    setattr(handler, _STREAM_HANDLER_MARKER, True)
    return handler


class _AgentLoopFileHandler(logging.Handler):
    def __init__(self, log_dir: Path) -> None:
        super().__init__(level=logging.DEBUG)
        self._log_dir = log_dir
        self._lock = Lock()
        self.setFormatter(_JsonLogFormatter())
        setattr(self, _AGENT_LOOP_HANDLER_MARKER, True)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            task_id = _record_context(record).get("task_id")
            log_path = get_agent_loop_log_path(str(task_id) if task_id else None)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            payload = self.format(record)
            with self._lock:
                with log_path.open("a", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.write("\n")
        except Exception:
            self.handleError(record)


def _remove_apmatia_handlers(root_logger: logging.Logger) -> None:
    for handler in list(root_logger.handlers):
        if getattr(handler, _FILE_HANDLER_MARKER, False) or getattr(handler, _STREAM_HANDLER_MARKER, False):
            root_logger.removeHandler(handler)


def _set_logger_levels(levels: dict[str, int]) -> None:
    for logger_name, level in levels.items():
        logging.getLogger(logger_name).setLevel(level)


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "pathname": record.pathname,
            "process": record.process,
            "thread": record.threadName,
        }
        context = _json_safe(_record_context(record))
        if context:
            payload["context"] = context
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _record_context(record: logging.LogRecord) -> dict[str, Any]:
    standard_keys = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }
    context = {
        key: value
        for key, value in record.__dict__.items()
        if key not in standard_keys and not key.startswith("_")
    }
    return context


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted(_json_safe(item) for item in value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "value") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return _json_safe(value.value)
        except Exception:
            return str(value)
    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        try:
            return _json_safe(value.to_dict())
        except Exception:
            return str(value)
    return value


def _read_structured_log_entries_from_file(log_file: Path, *, source: str) -> list[dict[str, Any]]:
    lines = deque(maxlen=_DEFAULT_TAIL_LIMIT)
    with log_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            clean_line = line.strip()
            if clean_line:
                lines.append(clean_line)

    entries: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        entries.append(_parse_log_entry(line, index=index, source=source))
    return entries


def _log_entry_sort_key(entry: dict[str, Any]) -> tuple[str, str]:
    return (str(entry.get("timestamp") or ""), str(entry.get("id") or ""))


def _parse_log_entry(line: str, *, index: int, source: str) -> dict[str, Any]:
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        return {
            "id": f"line-{index}",
            "timestamp": "",
            "level": "RAW",
            "logger": "",
            "message": line,
            "context": {},
            "raw": line,
            "source": source,
        }

    context = entry.get("context")
    if not isinstance(context, dict):
        context = {}

    message = str(entry.get("message") or "").strip()
    if not message and "exception" in entry:
        message = str(entry.get("exception") or "").strip()

    return {
        "id": f"line-{index}",
        "timestamp": str(entry.get("timestamp") or ""),
        "level": str(entry.get("level") or ""),
        "logger": str(entry.get("logger") or ""),
        "message": message,
        "context": context,
        "exception": str(entry.get("exception") or "").strip(),
        "module": str(entry.get("module") or ""),
        "function": str(entry.get("function") or ""),
        "line": entry.get("line"),
        "pathname": str(entry.get("pathname") or ""),
        "process": entry.get("process"),
        "thread": str(entry.get("thread") or ""),
        "source": source,
    }


def _sanitize_log_stem(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    normalized = normalized.strip("._-")
    return normalized or "agent_loop"


logger = get_logger(_LOGGER_NAME)
