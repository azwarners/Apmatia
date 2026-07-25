from __future__ import annotations

from unittest.mock import patch

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.modules.preferences.commands import COMMAND_DESCRIPTORS
from apmatia.modules.preferences.module import APMATIA_PREFERENCES_MODULE
from apmatia.modules.preferences.module_views import ApmatiaPreferencesModuleViewProvider
from apmatia.modules.preferences.views import VIEW_DESCRIPTORS


def test_preferences_module_is_stable_and_exposes_form_view() -> None:
    view = VIEW_DESCRIPTORS[0]

    assert APMATIA_PREFERENCES_MODULE.status == "stable"
    assert APMATIA_PREFERENCES_MODULE.default_enabled is True
    assert view.view_id == "preferences.preferences.view"
    assert view.metadata["ui"]["render_mode"] == "form"
    assert view.metadata["ui"]["form"]["fields"]


def test_preferences_provider_lists_current_preferences() -> None:
    provider = ApmatiaPreferencesModuleViewProvider()
    current = {"theme": "dark", "timezone": "America/Phoenix"}

    with patch("apmatia.modules.preferences.module_views.get_settings_payload", return_value=current):
        items = provider.list_items(view=VIEW_DESCRIPTORS[0], context=ModuleViewContext(user_id=1))

    assert items == [{"id": "preferences", **current}]


def test_preferences_provider_saves_and_returns_ui_preferences() -> None:
    provider = ApmatiaPreferencesModuleViewProvider()
    payload = {
        "llama_server_log_dir": "/logs",
        "gguf_directories": "/models",
        "auto_scan_gguf_directory": True,
        "llama_server_executable_path": "/usr/bin/llama-server",
        "llama_server_default_args": "--ctx-size 4096",
        "workspace_root": "/workspace",
        "knowledge_root": "/knowledge",
        "timezone": "America/Phoenix",
        "theme": "dark",
        "font_family": "system-ui",
        "accent_color": "#ff6b6b",
        "font_size": 16,
        "title_bar_height": 56,
        "title_bar_font_size": 20,
        "terminal_background_color": "#000000",
        "terminal_text_color": "#9dffad",
        "terminal_border_color": "rgba(110, 255, 170, 0.35)",
        "terminal_muted_color": "rgba(157, 255, 173, 0.72)",
    }

    with patch("apmatia.modules.preferences.module_views.save_settings_payload") as save, patch(
        "apmatia.modules.preferences.module_views.get_settings_payload", return_value=payload
    ):
        result = provider.execute_command(
            command=COMMAND_DESCRIPTORS[0],
            payload=payload,
            context=ModuleViewContext(user_id=1),
        )

    save.assert_called_once_with(**payload)
    assert result == {
        "status": "saved",
        "message": "Preferences saved.",
        "item": {"id": "preferences", **payload},
        "ui_preferences": payload,
    }
