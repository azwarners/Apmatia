from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import Registry


def test_logging_module_registers_module_metadata_and_view_descriptors(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APMATIA_LOG_FILE", str(tmp_path / "apmatia.jsonl"))

    module = importlib.import_module("apmatia.modules.logging.module")
    module = importlib.reload(module)

    registry = Registry()
    module.register(registry)

    assert [module.module_id for module in registry.list_modules()] == ["logging"]
    assert [view.view_id for view in registry.list_views()] == ["logging.entries.view"]


def test_logging_module_view_provider_reads_structured_log_entries(monkeypatch, tmp_path: Path):
    log_file = tmp_path / "apmatia.jsonl"
    monkeypatch.setenv("APMATIA_LOG_FILE", str(log_file))

    log_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-07-15T12:34:56.789+00:00",
                        "level": "INFO",
                        "logger": "apmatia.interfaces.streamlit.page_runtime",
                        "message": "Page generation advanced",
                        "module": "page_runtime",
                        "function": "sync_page_generation",
                        "line": 21,
                        "pathname": "/home/nick/ServerData/repos/apmatia/src/apmatia/interfaces/streamlit/page_runtime.py",
                        "process": 1234,
                        "thread": "MainThread",
                        "context": {
                            "selected_page": "module_view",
                            "selected_page_detail": "agent_loops:agent_loops.tasks.view",
                            "selected_module_id": "agent_loops",
                            "selected_module_view_id": "agent_loops.tasks.view",
                            "page_signature": "module_view:agent_loops:agent_loops.tasks.view",
                            "page_generation": 12,
                        },
                    }
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    module_views = importlib.import_module("apmatia.modules.logging.module_views")
    module_views = importlib.reload(module_views)

    provider = module_views.ApmatiaLoggingModuleViewProvider()
    view = importlib.import_module("apmatia.modules.logging.views").VIEW_DESCRIPTORS[0]
    items = provider.list_items(view=view, context=ModuleViewContext())

    assert len(items) == 1
    assert items[0]["level"] == "INFO"
    assert items[0]["logger"] == "apmatia.interfaces.streamlit.page_runtime"
    assert items[0]["message"] == "Page generation advanced"
    assert items[0]["context_summary"] == (
        "selected_page=module_view, "
        "selected_page_detail=agent_loops:agent_loops.tasks.view, "
        "selected_module_id=agent_loops, "
        "selected_module_view_id=agent_loops.tasks.view, "
        "page_signature=module_view:agent_loops:agent_loops.tasks.view, "
        "page_generation=12"
    )


def test_logging_configuration_suppresses_watchdog_debug_noise(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APMATIA_LOG_FILE", str(tmp_path / "apmatia.jsonl"))

    logger_module = importlib.import_module("apmatia.lib.persistence.logger")
    logger_module = importlib.reload(logger_module)
    logger_module.clear_log_file()

    logging.getLogger("watchdog.observers.inotify_buffer").debug("filesystem noise")
    logging.getLogger("apmatia.tests.logging").info("useful app event")

    entries = logger_module.read_structured_log_entries(limit=10)

    assert [entry["message"] for entry in entries] == ["useful app event"]
    assert all(entry["logger"] != "watchdog.observers.inotify_buffer" for entry in entries)
