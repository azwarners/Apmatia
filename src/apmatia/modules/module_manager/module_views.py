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


class ApmatiaModuleManagerViewProvider:
    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        del view, context
        activation = get_module_activation()
        show_development_modules = bool(activation.get("show_development_modules", False))
        return [
            {
                "id": "module_catalog",
                "show_development_modules": show_development_modules,
                "modules": list_module_catalog(include_development=show_development_modules),
            }
        ]

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        del context
        verb = str(command.metadata.get("verb") or "").strip().lower()

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
            if module_id == "module_manager" and _require_bool(payload, "hidden"):
                raise ValueError("The Module Manager cannot hide itself.")
            item = set_module_hidden(module_id, hidden=_require_bool(payload, "hidden"))
            return {"status": "updated", "message": "Module visibility updated.", "item": item}

        if verb == "set_module_order":
            module_id = _require_identifier(payload, "module_id")
            item = set_module_order(module_id, new_index=_require_index(payload, "new_index"))
            return {"status": "updated", "message": "Module order updated.", "item": item}

        if verb == "set_view_visibility":
            view_id = _require_identifier(payload, "view_id")
            if view_id == "module_manager.module_manager.view" and _require_bool(payload, "hidden"):
                raise ValueError("The Module Manager view cannot hide itself.")
            item = set_view_hidden(view_id, hidden=_require_bool(payload, "hidden"))
            return {"status": "updated", "message": "View visibility updated.", "item": item}

        if verb == "set_view_order":
            module_id = _require_identifier(payload, "module_id")
            view_id = _require_identifier(payload, "view_id")
            item = set_view_order(
                module_id,
                view_id,
                new_index=_require_index(payload, "new_index"),
            )
            return {"status": "updated", "message": "View order updated.", "item": item}

        raise ValueError(f"Unsupported Module Manager command verb: {verb}")


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
