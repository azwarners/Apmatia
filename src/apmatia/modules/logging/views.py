from __future__ import annotations

from apmatia.core.registry import ViewContribution


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="logging",
        action_id="logging.entries",
        view_id="logging.entries.view",
        name="Application Logs",
        description="Browse recent structured application log events.",
        metadata={
            "object_type": "log_entry",
            "singular_label": "Log entry",
            "plural_label": "Log entries",
            "empty_state": "No log entries have been recorded yet.",
            "ui": {
                "render_mode": "collection",
                "title": "Application Logs",
                "caption": "Recent runtime events, warnings, and errors recorded by Apmatia.",
                "empty_state": "No log entries have been recorded yet.",
                "item_key": "id",
                "columns": [
                    {"key": "timestamp", "label": "Time"},
                    {"key": "level", "label": "Level"},
                    {"key": "logger", "label": "Logger"},
                    {"key": "message", "label": "Message"},
                    {"key": "context_summary", "label": "Context"},
                ],
            },
        },
    ),
)

