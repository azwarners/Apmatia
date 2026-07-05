from __future__ import annotations

from apmatia.core.registry import (
    create_application_registry,
    get_application_registry,
    load_bundled_modules,
    Registry,
)
from apmatia.core.registry import bootstrap


def test_load_bundled_modules_loads_bundled_modules():
    registry = load_bundled_modules(Registry())

    assert [module.module_id for module in registry.list_modules()] == [
        "apmatia_ai_host_management",
        "apmatia_ai_model_executor",
        "apmatia_ai_model_manager",
        "apmatia_ipe",
        "apmatia_source_inspection",
        "apmatia_worksim",
    ]
    assert [action.action_id for action in registry.list_actions()] == [
        "apmatia_ai_host_management.hosts",
        "apmatia_ai_host_management.resources",
        "apmatia_ai_model_executor.executions",
        "apmatia_ai_model_executor.resources",
        "apmatia_ai_model_manager.models",
        "apmatia_ai_model_manager.preferences",
        "apmatia_ipe.calendar_event",
        "apmatia_ipe.habit",
        "apmatia_ipe.idea",
        "apmatia_ipe.project",
        "apmatia_ipe.task",
        "apmatia_worksim.org_chart_node",
    ]
    assert [command.command_id for command in registry.list_commands()] == [
        "apmatia_ai_host_management.hosts.create",
        "apmatia_ai_host_management.hosts.delete",
        "apmatia_ai_host_management.hosts.disable",
        "apmatia_ai_host_management.hosts.edit",
        "apmatia_ai_host_management.hosts.list",
        "apmatia_ai_host_management.hosts.prepare_ssh_copy_command",
        "apmatia_ai_host_management.hosts.prepare_ssh_key",
        "apmatia_ai_host_management.resources.inspect_local",
        "apmatia_ai_host_management.resources.validate",
        "apmatia_ai_model_executor.executions.can_run",
        "apmatia_ai_model_executor.executions.start",
        "apmatia_ai_model_executor.executions.status",
        "apmatia_ai_model_executor.executions.stop",
        "apmatia_ai_model_executor.resources.inspect",
        "apmatia_ai_model_manager.models.create",
        "apmatia_ai_model_manager.models.delete",
        "apmatia_ai_model_manager.models.edit",
        "apmatia_ai_model_manager.models.list",
        "apmatia_ai_model_manager.models.scan",
        "apmatia_ai_model_manager.models.show",
        "apmatia_ai_model_manager.preferences.create",
        "apmatia_ai_model_manager.preferences.delete",
        "apmatia_ai_model_manager.preferences.edit",
        "apmatia_ai_model_manager.preferences.list",
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
        "apmatia_worksim.org_chart_node.create",
        "apmatia_worksim.org_chart_node.delete",
        "apmatia_worksim.org_chart_node.edit",
        "apmatia_worksim.org_chart_node.list",
    ]
    assert [view.view_id for view in registry.list_views()] == [
        "apmatia_ai_host_management.hosts.view",
        "apmatia_ai_host_management.resources.view",
        "apmatia_ai_model_manager.models.view",
        "apmatia_ai_model_manager.preferences.view",
        "apmatia_ipe.calendar_event.view",
        "apmatia_ipe.habit.view",
        "apmatia_ipe.idea.view",
        "apmatia_ipe.project.view",
        "apmatia_ipe.task.view",
        "apmatia_worksim.org_chart_node.view",
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
    assert [module.module_id for module in first.list_modules()] == [
        "apmatia_ai_host_management",
        "apmatia_ai_model_executor",
        "apmatia_ai_model_manager",
        "apmatia_ipe",
        "apmatia_source_inspection",
        "apmatia_worksim",
    ]
