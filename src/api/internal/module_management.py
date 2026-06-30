from __future__ import annotations

from src.core.module_management import (
    get_module_catalog_entry,
    get_view_catalog_entry,
    list_module_catalog,
    set_module_hidden,
    set_view_hidden,
)


def list_modules() -> list[dict]:
    return list_module_catalog()


def update_module_visibility(module_id: str, *, hidden: bool) -> dict:
    return get_module_catalog_entry(module_id) if hidden is None else set_module_hidden(module_id, hidden=hidden)


def update_view_visibility(view_id: str, *, hidden: bool) -> dict:
    return get_view_catalog_entry(view_id) if hidden is None else set_view_hidden(view_id, hidden=hidden)
