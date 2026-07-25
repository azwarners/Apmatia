from __future__ import annotations

from apmatia.core.module_management import (
    get_module_catalog_entry,
    get_module_activation,
    get_view_catalog_entry,
    list_module_catalog,
    set_module_order,
    set_module_hidden,
    set_view_order,
    set_view_hidden,
    set_development_modules_enabled,
)


def list_modules(*, include_development: bool = False) -> list[dict]:
    return list_module_catalog(include_development=include_development)


def get_module_activation_state() -> dict:
    return get_module_activation()


def update_development_modules(*, enabled: bool) -> dict:
    return set_development_modules_enabled(enabled)


def update_module_visibility(module_id: str, *, hidden: bool) -> dict:
    return get_module_catalog_entry(module_id) if hidden is None else set_module_hidden(module_id, hidden=hidden)


def update_view_visibility(view_id: str, *, hidden: bool) -> dict:
    return get_view_catalog_entry(view_id) if hidden is None else set_view_hidden(view_id, hidden=hidden)


def update_view_order(module_id: str, view_id: str, *, new_index: int) -> dict:
    return set_view_order(module_id, view_id, new_index=new_index)


def update_module_order(module_id: str, *, new_index: int) -> dict:
    return set_module_order(module_id, new_index=new_index)
