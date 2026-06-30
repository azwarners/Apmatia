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

    assert [module.module_id for module in registry.list_modules()] == ["apmatia_ipe", "example"]
    assert [action.action_id for action in registry.list_actions()] == [
        "apmatia_ipe.calendar_event",
        "apmatia_ipe.habit",
        "apmatia_ipe.idea",
        "apmatia_ipe.project",
        "apmatia_ipe.task",
        "example.action",
    ]
    assert [command.command_id for command in registry.list_commands()] == [
        "apmatia_ipe.calendar_event.create",
        "apmatia_ipe.calendar_event.delete",
        "apmatia_ipe.calendar_event.edit",
        "apmatia_ipe.calendar_event.list",
        "apmatia_ipe.habit.create",
        "apmatia_ipe.habit.delete",
        "apmatia_ipe.habit.edit",
        "apmatia_ipe.habit.list",
        "apmatia_ipe.idea.create",
        "apmatia_ipe.idea.delete",
        "apmatia_ipe.idea.edit",
        "apmatia_ipe.idea.list",
        "apmatia_ipe.project.create",
        "apmatia_ipe.project.delete",
        "apmatia_ipe.project.edit",
        "apmatia_ipe.project.list",
        "apmatia_ipe.task.create",
        "apmatia_ipe.task.delete",
        "apmatia_ipe.task.edit",
        "apmatia_ipe.task.list",
        "example.command",
    ]
    assert [view.view_id for view in registry.list_views()] == [
        "apmatia_ipe.calendar_event.view",
        "apmatia_ipe.habit.view",
        "apmatia_ipe.idea.view",
        "apmatia_ipe.project.view",
        "apmatia_ipe.task.view",
        "example.view",
    ]


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
    assert [module.module_id for module in first.list_modules()] == ["apmatia_ipe", "example"]
