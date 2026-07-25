from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution
from apmatia.modules.persistence.logger import read_structured_log_entries


class ApmatiaLoggingModuleViewProvider:
    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        object_type = str(view.metadata.get("object_type") or "").strip().lower()
        if object_type != "log_entry":
            raise ValueError(f"Unsupported logging view type: {object_type}")

        entries = read_structured_log_entries(limit=250, include_agent_loop_logs=True)
        return [_log_entry_to_item(entry) for entry in entries]

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        raise ValueError(f"Unsupported logging command: {command.command_id}")


def _log_entry_to_item(entry: dict[str, Any]) -> dict[str, Any]:
    context = entry.get("context") if isinstance(entry.get("context"), dict) else {}
    return {
        "id": entry.get("id"),
        "timestamp": entry.get("timestamp"),
        "level": entry.get("level"),
        "logger": entry.get("logger"),
        "message": entry.get("message"),
        "context": context,
        "context_summary": _context_summary(context),
        "exception": entry.get("exception"),
        "module": entry.get("module"),
        "function": entry.get("function"),
        "line": entry.get("line"),
        "pathname": entry.get("pathname"),
        "process": entry.get("process"),
        "thread": entry.get("thread"),
        "source": entry.get("source"),
        "raw": entry.get("raw"),
    }


def _context_summary(context: dict[str, Any]) -> str:
    if not context:
        return ""
    interesting_keys = (
        "source",
        "selected_page",
        "selected_page_detail",
        "selected_module_id",
        "selected_module_view_id",
        "page_signature",
        "page_generation",
    )
    parts = []
    for key in interesting_keys:
        value = context.get(key)
        if value in (None, ""):
            continue
        parts.append(f"{key}={value}")
    if parts:
        return ", ".join(parts)
    return ", ".join(f"{key}={value}" for key, value in sorted(context.items()))
