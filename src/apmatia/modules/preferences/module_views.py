from __future__ import annotations

from typing import Any, Mapping

from apmatia.core.module_management import (
    get_module_activation,
    list_module_catalog,
    set_development_modules_enabled,
    set_module_hidden,
    set_module_order,
    set_view_hidden,
    set_view_order,
)
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
        del context
        if str(view.metadata.get("object_type") or "") == "module_catalog":
            activation = get_module_activation()
            show_development_modules = bool(activation.get("show_development_modules", False))
            modules = list_module_catalog(include_development=show_development_modules)
            items: list[dict[str, Any]] = [{
                "id": "activation", "item_kind": "activation", "name": "Enable all modules",
                "enabled": show_development_modules, "hidden": False, "new_index": 0,
            }]
            for module_index, module in enumerate(modules):
                module_id = str(module.get("module_id") or "")
                items.append({**module, "id": f"module:{module_id}", "item_kind": "module", "new_index": module_index})
                for view_index, item in enumerate(module.get("views") or []):
                    if isinstance(item, Mapping):
                        items.append({**item, "id": f"view:{item.get('view_id')}", "item_kind": "view", "module_id": module_id, "new_index": view_index})
            return items
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
        if str(command.metadata.get("object_type") or "") == "module_catalog":
            return _execute_module_command(verb, payload)
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


def _execute_module_command(verb: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if verb == "update_catalog_item":
        kind = str(payload.get("item_kind") or "")
        if kind == "activation":
            return _execute_module_command("set_activation", {"enabled": bool(payload.get("enabled"))})
        if kind == "module":
            module_id = _require_identifier(payload, "module_id")
            set_module_hidden(module_id, hidden=bool(payload.get("hidden")))
            item = set_module_order(module_id, new_index=_require_index(payload, "new_index"))
            return {"status": "updated", "message": "Module updated.", "item": item}
        if kind == "view":
            module_id = _require_identifier(payload, "module_id")
            view_id = _require_identifier(payload, "view_id")
            set_view_hidden(view_id, hidden=bool(payload.get("hidden")))
            item = set_view_order(module_id, view_id, new_index=_require_index(payload, "new_index"))
            return {"status": "updated", "message": "View updated.", "item": item}
        raise ValueError(f"Unsupported catalog item kind: {kind}")
    if verb == "set_activation":
        enabled = _require_bool(payload, "enabled")
        activation = set_development_modules_enabled(enabled)
        return {
            "status": "updated",
            "message": "All modules enabled." if enabled else "Stable modules only enabled.",
            "activation": activation,
        }

    if verb == "set_module_visibility":
        module_id = _require_identifier(payload, "module_id")
        hidden = _require_bool(payload, "hidden")
        if module_id == "preferences" and hidden:
            raise ValueError("Preferences cannot hide itself.")
        item = set_module_hidden(module_id, hidden=hidden)
        return {"status": "updated", "message": "Module visibility updated.", "item": item}

    if verb == "set_module_order":
        module_id = _require_identifier(payload, "module_id")
        item = set_module_order(module_id, new_index=_require_index(payload, "new_index"))
        return {"status": "updated", "message": "Module order updated.", "item": item}

    if verb == "set_view_visibility":
        view_id = _require_identifier(payload, "view_id")
        hidden = _require_bool(payload, "hidden")
        if view_id == "preferences.modules.view" and hidden:
            raise ValueError("The Modules view cannot hide itself.")
        item = set_view_hidden(view_id, hidden=hidden)
        return {"status": "updated", "message": "View visibility updated.", "item": item}

    if verb == "set_view_order":
        module_id = _require_identifier(payload, "module_id")
        view_id = _require_identifier(payload, "view_id")
        item = set_view_order(module_id, view_id, new_index=_require_index(payload, "new_index"))
        return {"status": "updated", "message": "View order updated.", "item": item}

    raise ValueError(f"Unsupported Preferences command verb: {verb}")


def _require_identifier(payload: Mapping[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key.replace('_', ' ').title()} cannot be empty.")
    return value


def _require_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key.replace('_', ' ').title()} must be a boolean.")
    return value


def _require_index(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool):
        raise ValueError(f"{key.replace('_', ' ').title()} must be an integer.")
    try:
        index = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{key.replace('_', ' ').title()} must be an integer.") from error
    if index < 0:
        raise ValueError(f"{key.replace('_', ' ').title()} cannot be negative.")
    return index
