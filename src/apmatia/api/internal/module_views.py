from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apmatia.api.internal.group_access import enabled_group_ids
from apmatia.api.internal.users import list_user_groups
from apmatia.core.module_view_runtime import execute_module_command, list_module_view_items
from apmatia.core.registry import get_application_registry
from apmatia.core.view_contract import normalize_view_document


def list_module_view_documents() -> list[dict[str, Any]]:
    """Return every active registry view as a deterministic portable document."""
    registry = get_application_registry()
    return [normalize_view_document(view).to_dict() for view in registry.list_views()]


def get_module_view_document(view_id: str) -> dict[str, Any]:
    """Return one active registry view as a portable document."""
    normalized_view_id = view_id.strip()
    for view in get_application_registry().list_views():
        if view.view_id == normalized_view_id:
            return normalize_view_document(view).to_dict()
    raise ValueError(f"Unknown module view: {view_id}")


def list_module_commands() -> list[dict[str, Any]]:
    registry = get_application_registry()
    modules = {module.module_id: module for module in registry.list_modules(include_development=True)}
    views = {view.view_id: view for view in registry.list_views()}
    catalog: list[dict[str, Any]] = []
    for command in registry.list_commands():
        metadata = dict(command.metadata or {})
        module = modules.get(command.module_id)
        path = list(command.path or tuple(command.command_id.split(".")))
        catalog.append(
            {
                "module_id": command.module_id,
                "module_name": getattr(module, "name", command.module_id.replace("_", " ").title()),
                "module_description": getattr(module, "description", ""),
                "command_id": command.command_id,
                "path": path,
                "name": command.name,
                "description": command.description,
                "fields": _command_fields(metadata, views),
                "metadata": metadata,
            }
        )
    return catalog


def _command_fields(metadata: dict[str, Any], views: Mapping[str, Any]) -> list[dict[str, Any]]:
    explicit = metadata.get("input_fields")
    if isinstance(explicit, list):
        return [dict(field) for field in explicit if isinstance(field, Mapping)]

    verb = str(metadata.get("verb") or "").strip().lower()
    view_id = str(metadata.get("collection_view_id") or "").strip()
    view = views.get(view_id)
    view_metadata = dict(getattr(view, "metadata", {}) or {}) if view is not None else {}
    fields: list[dict[str, Any]] = []
    if verb in {"create", "edit"}:
        schema = view_metadata.get("schema")
        raw_fields = schema.get("fields") if isinstance(schema, Mapping) else None
        if isinstance(raw_fields, list):
            fields.extend(
                dict(field)
                for field in raw_fields
                if isinstance(field, Mapping) and bool(field.get(verb, False))
            )
    elif verb == "save":
        ui = view_metadata.get("ui")
        form = ui.get("form") if isinstance(ui, Mapping) else None
        raw_fields = form.get("fields") if isinstance(form, Mapping) else None
        if isinstance(raw_fields, list):
            fields.extend(dict(field) for field in raw_fields if isinstance(field, Mapping))

    if verb in {"edit", "delete"} and view_id and not any(field.get("key") == "item_id" for field in fields):
        fields.insert(
            0,
            {
                "key": "item_id",
                "label": "Item ID",
                "data_type": "number",
                "field_type": "number",
                "required": True,
            },
        )
    return fields


def get_module_view_items(view_id: str, *, user_id: int) -> list[dict[str, Any]]:
    return list_module_view_items(
        view_id,
        user_id=user_id,
        group_ids=enabled_group_ids(list_user_groups(user_id)),
    )


def run_module_command(
    command_id: str,
    *,
    payload: Mapping[str, Any] | None = None,
    user_id: int,
) -> dict[str, Any] | None:
    return execute_module_command(
        command_id,
        payload=payload,
        user_id=user_id,
        group_ids=enabled_group_ids(list_user_groups(user_id)),
    )
