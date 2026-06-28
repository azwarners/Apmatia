from __future__ import annotations

from src.core.registry import (
    create_application_registry,
    get_application_registry,
    load_bundled_modules,
    Registry,
)
from src.core.registry import bootstrap


def test_load_bundled_modules_loads_example_module():
    registry = load_bundled_modules(Registry())

    assert [module.module_id for module in registry.list_modules()] == ["example"]
    assert [action.action_id for action in registry.list_actions()] == ["example.action"]
    assert [command.command_id for command in registry.list_commands()] == ["example.command"]
    assert [view.view_id for view in registry.list_views()] == ["example.view"]


def test_create_application_registry_loads_bundled_modules():
    registry = create_application_registry()

    assert registry.list_modules()
    assert registry.list_actions()
    assert registry.list_commands()
    assert registry.list_views()


def test_get_application_registry_returns_cached_registry():
    bootstrap.get_application_registry.cache_clear()

    first = get_application_registry()
    second = get_application_registry()

    assert first is second
    assert [module.module_id for module in first.list_modules()] == ["example"]
