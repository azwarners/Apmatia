from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from src.core.app_config import get_config_value, set_config_value
from src.core.registry import get_application_registry


def list_module_catalog() -> list[dict[str, Any]]:
    registry = get_application_registry()
    hidden_module_ids = _hidden_identifier_set(get_config_value("ui", "hidden_module_ids", default=[]))
    hidden_view_ids = _hidden_identifier_set(get_config_value("ui", "hidden_view_ids", default=[]))

    views_by_module: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for view in registry.list_views():
        metadata = dict(getattr(view, "metadata", {}) or {})
        explicitly_hidden = view.view_id in hidden_view_ids
        views_by_module[view.module_id].append(
            {
                "view_id": view.view_id,
                "action_id": view.action_id,
                "name": view.name,
                "description": view.description,
                "metadata": metadata,
                "hidden": explicitly_hidden,
            }
        )

    catalog: list[dict[str, Any]] = []
    for module in registry.list_modules():
        metadata = dict(getattr(module, "metadata", {}) or {})
        module_hidden = module.module_id in hidden_module_ids
        raw_views = sorted(views_by_module.get(module.module_id, []), key=lambda item: str(item["view_id"]))
        serialized_views = [
            {
                **view,
                "effective_hidden": bool(module_hidden or view["hidden"]),
            }
            for view in raw_views
        ]
        visible_view_count = sum(0 if view["effective_hidden"] else 1 for view in serialized_views)
        catalog.append(
            {
                "module_id": module.module_id,
                "name": module.name,
                "version": module.version,
                "description": module.description,
                "metadata": metadata,
                "hidden": module_hidden,
                "views": serialized_views,
                "view_count": len(serialized_views),
                "visible_view_count": visible_view_count,
            }
        )
    return catalog


def set_module_hidden(module_id: str, *, hidden: bool) -> dict[str, Any]:
    normalized_module_id = _require_known_module(module_id)
    hidden_module_ids = _hidden_identifier_set(get_config_value("ui", "hidden_module_ids", default=[]))
    if hidden:
        hidden_module_ids.add(normalized_module_id)
    else:
        hidden_module_ids.discard(normalized_module_id)
    set_config_value("ui", "hidden_module_ids", value=sorted(hidden_module_ids))
    return get_module_catalog_entry(normalized_module_id)


def set_view_hidden(view_id: str, *, hidden: bool) -> dict[str, Any]:
    normalized_view_id = _require_known_view(view_id)
    hidden_view_ids = _hidden_identifier_set(get_config_value("ui", "hidden_view_ids", default=[]))
    if hidden:
        hidden_view_ids.add(normalized_view_id)
    else:
        hidden_view_ids.discard(normalized_view_id)
    set_config_value("ui", "hidden_view_ids", value=sorted(hidden_view_ids))
    return get_view_catalog_entry(normalized_view_id)


def get_module_catalog_entry(module_id: str) -> dict[str, Any]:
    normalized_module_id = module_id.strip()
    for entry in list_module_catalog():
        if entry["module_id"] == normalized_module_id:
            return entry
    raise ValueError(f"Unknown module: {module_id}")


def get_view_catalog_entry(view_id: str) -> dict[str, Any]:
    normalized_view_id = view_id.strip()
    for module in list_module_catalog():
        for view in module["views"]:
            if view["view_id"] == normalized_view_id:
                return {
                    **view,
                    "module_id": module["module_id"],
                    "module_name": module["name"],
                    "module_hidden": module["hidden"],
                }
    raise ValueError(f"Unknown view: {view_id}")


def _hidden_identifier_set(values: Any) -> set[str]:
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes, dict)):
        return set()
    hidden_ids: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text:
            hidden_ids.add(text)
    return hidden_ids


def _require_known_module(module_id: str) -> str:
    normalized_module_id = str(module_id or "").strip()
    if not normalized_module_id:
        raise ValueError("Module ID cannot be empty.")
    known_module_ids = {module.module_id for module in get_application_registry().list_modules()}
    if normalized_module_id not in known_module_ids:
        raise ValueError(f"Unknown module: {module_id}")
    return normalized_module_id


def _require_known_view(view_id: str) -> str:
    normalized_view_id = str(view_id or "").strip()
    if not normalized_view_id:
        raise ValueError("View ID cannot be empty.")
    known_view_ids = {view.view_id for view in get_application_registry().list_views()}
    if normalized_view_id not in known_view_ids:
        raise ValueError(f"Unknown view: {view_id}")
    return normalized_view_id
