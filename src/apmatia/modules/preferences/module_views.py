from __future__ import annotations

from typing import Any, Mapping

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution
from apmatia.core.settings_service import get_settings_payload, save_settings_payload


class ApmatiaPreferencesModuleViewProvider:
    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        del view, context
        return [{"id": "preferences", **get_settings_payload()}]

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        del context
        verb = str(command.metadata.get("verb") or "").strip().lower()
        if verb != "save":
            raise ValueError(f"Unsupported Preferences command verb: {verb}")

        save_settings_payload(
            llama_server_log_dir=str(payload.get("llama_server_log_dir") or ""),
            gguf_directories=str(payload.get("gguf_directories") or payload.get("gguf_directory") or ""),
            auto_scan_gguf_directory=bool(payload.get("auto_scan_gguf_directory", True)),
            llama_server_executable_path=str(payload.get("llama_server_executable_path") or "llama-server"),
            llama_server_default_args=str(payload.get("llama_server_default_args") or ""),
            workspace_root=str(payload.get("workspace_root") or ""),
            knowledge_root=str(payload.get("knowledge_root") or ""),
            timezone=str(payload.get("timezone") or "America/Phoenix"),
            theme=str(payload.get("theme") or "dark"),
            font_family=str(payload.get("font_family") or "system-ui"),
            accent_color=str(payload.get("accent_color") or "#ff6b6b"),
            font_size=int(payload.get("font_size") or 16),
            title_bar_height=int(payload.get("title_bar_height") or 56),
            title_bar_font_size=int(payload.get("title_bar_font_size") or 20),
            terminal_background_color=str(payload.get("terminal_background_color") or "#000000"),
            terminal_text_color=str(payload.get("terminal_text_color") or "#9dffad"),
            terminal_border_color=str(payload.get("terminal_border_color") or "rgba(110, 255, 170, 0.35)"),
            terminal_muted_color=str(payload.get("terminal_muted_color") or "rgba(157, 255, 173, 0.72)"),
        )
        current = get_settings_payload()
        return {
            "status": "saved",
            "message": "Preferences saved.",
            "item": {"id": "preferences", **current},
            "ui_preferences": current,
        }
