from __future__ import annotations

import json
import logging
import os
from collections import deque
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from apmatia.core.runtime_paths import get_app_dir


_LOGGER_NAME = "apmatia"
_FILE_HANDLER_MARKER = "_apmatia_file_handler"
_STREAM_HANDLER_MARKER = "_apmatia_stream_handler"
_CONFIGURED_MARKER = "_apmatia_logging_configured"
_DEFAULT_LOG_BASENAME = "apmatia.jsonl"
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


def get_logger(name: str | None = None) -> logging.Logger:
    configure_logging()
    normalized_name = str(name or _LOGGER_NAME).strip() or _LOGGER_NAME
    return logging.getLogger(normalized_name)


def read_structured_log_entries(*, limit: int = _DEFAULT_TAIL_LIMIT) -> list[dict[str, Any]]:
    log_file = get_log_file_path()
    if limit <= 0 or not log_file.exists():
        return []

    lines = deque(maxlen=limit)
    with log_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            clean_line = line.strip()
            if clean_line:
                lines.append(clean_line)

    entries: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        entries.append(_parse_log_entry(line, index=index))
    return entries


def clear_log_file() -> None:
    log_file = get_log_file_path()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("", encoding="utf-8")


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
        context = _record_context(record)
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


def _parse_log_entry(line: str, *, index: int) -> dict[str, Any]:
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
    }


logger = get_logger(_LOGGER_NAME)
