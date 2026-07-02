from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from apmatia.core.app_config import get_config_value, set_config_value
from apmatia.core.registry import get_application_registry


def list_module_catalog() -> list[dict[str, Any]]:
    registry = get_application_registry()
    hidden_module_ids = _hidden_identifier_set(get_config_value("ui", "hidden_module_ids", default=[]))
    hidden_view_ids = _hidden_identifier_set(get_config_value("ui", "hidden_view_ids", default=[]))
    view_orders = _view_order_map()

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
        raw_views = _ordered_views(module.module_id, views_by_module.get(module.module_id, []), view_orders)
        serialized_views = [
            {
                **view,
                "effective_hidden": bool(module_hidden or view["hidden"]),
                "sort_order": index,
            }
            for index, view in enumerate(raw_views)
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


def set_view_order(module_id: str, view_id: str, *, new_index: int) -> dict[str, Any]:
    normalized_module_id = _require_known_module(module_id)
    normalized_view_id = _require_known_view(view_id)
    if new_index < 0:
        raise ValueError("View order cannot be negative.")

    registry = get_application_registry()
    module_views = [view for view in registry.list_views() if view.module_id == normalized_module_id]
    if normalized_view_id not in {view.view_id for view in module_views}:
        raise ValueError(f"View does not belong to module: {view_id}")

    current_orders = _view_order_map()
    ordered_views = _ordered_views(
        normalized_module_id,
        [
            {
                "view_id": view.view_id,
                "action_id": view.action_id,
                "name": view.name,
                "description": view.description,
                "metadata": dict(getattr(view, "metadata", {}) or {}),
                "hidden": False,
            }
            for view in module_views
        ],
        current_orders,
    )
    module_view_ids = [str(view["view_id"]) for view in ordered_views]
    ordered_view_ids = _apply_view_order(
        module_view_ids,
        normalized_view_id,
        new_index,
    )
    view_orders = current_orders
    view_orders[normalized_module_id] = ordered_view_ids
    set_config_value("ui", "module_view_orders", value=view_orders)
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


def _view_order_map() -> dict[str, list[str]]:
    raw_orders = get_config_value("ui", "module_view_orders", default={})
    if not isinstance(raw_orders, dict):
        return {}

    orders: dict[str, list[str]] = {}
    for module_id, value in raw_orders.items():
        if not isinstance(module_id, str):
            continue
        ordered_ids = _ordered_identifier_list(value)
        if ordered_ids:
            orders[module_id] = ordered_ids
    return orders


def _ordered_identifier_list(value: Any) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, dict)):
        return []

    ordered_ids: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if text and text not in seen:
            ordered_ids.append(text)
            seen.add(text)
    return ordered_ids


def _ordered_views(
    module_id: str,
    views: list[dict[str, Any]],
    view_orders: dict[str, list[str]],
) -> list[dict[str, Any]]:
    if not views:
        return []

    indexed_views = {str(view["view_id"]): view for view in views}
    ordered_view_ids = [view_id for view_id in view_orders.get(module_id, []) if view_id in indexed_views]
    remaining_view_ids = sorted(view_id for view_id in indexed_views if view_id not in ordered_view_ids)
    return [indexed_views[view_id] for view_id in [*ordered_view_ids, *remaining_view_ids]]


def _apply_view_order(current_view_ids: list[str], view_id: str, new_index: int) -> list[str]:
    ordered_ids = [identifier for identifier in current_view_ids if identifier]
    if view_id not in ordered_ids:
        raise ValueError(f"View does not belong to module: {view_id}")

    ordered_ids.remove(view_id)
    target_index = min(new_index, len(ordered_ids))
    ordered_ids.insert(target_index, view_id)
    return ordered_ids


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
