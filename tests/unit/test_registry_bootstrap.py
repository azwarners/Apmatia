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
        "agent_alarms",
        "agent_config",
        "agent_loops",
        "ai_host_management",
        "ai_model_executor",
        "ai_model_manager",
        "contacts_and_discussions",
        "ipe",
        "source_inspection",
        "worksim",
    ]
    assert [action.action_id for action in registry.list_actions()] == [
        "agent_alarms.alarms",
        "agent_config.agent_config",
        "ai_host_management.hosts",
        "ai_host_management.resources",
        "ai_model_executor.executions",
        "ai_model_executor.resources",
        "ai_model_manager.models",
        "ai_model_manager.preferences",
        "contacts_and_discussions.chat_targets",
        "contacts_and_discussions.discussions",
        "contacts_and_discussions.summaries",
        "contacts_and_discussions.topics",
        "contacts_and_discussions.turns",
        "ipe.calendar_event",
        "ipe.habit",
        "ipe.idea",
        "ipe.project",
        "ipe.task",
        "worksim.org_chart_node",
    ]
    assert [command.command_id for command in registry.list_commands()] == [
        "agent_alarms.alarms.create",
        "agent_alarms.alarms.delete",
        "agent_alarms.alarms.edit",
        "agent_alarms.alarms.list",
        "agent_config.agent_config.save",
        "agent_loops.tasks.stop",
        "ai_host_management.hosts.create",
        "ai_host_management.hosts.delete",
        "ai_host_management.hosts.disable",
        "ai_host_management.hosts.edit",
        "ai_host_management.hosts.list",
        "ai_host_management.hosts.prepare_ssh_copy_command",
        "ai_host_management.hosts.prepare_ssh_key",
        "ai_host_management.resources.inspect_local",
        "ai_host_management.resources.validate",
        "ai_model_executor.executions.can_run",
        "ai_model_executor.executions.start",
        "ai_model_executor.executions.status",
        "ai_model_executor.executions.stop",
        "ai_model_executor.resources.inspect",
        "ai_model_manager.models.create",
        "ai_model_manager.models.delete",
        "ai_model_manager.models.edit",
        "ai_model_manager.models.list",
        "ai_model_manager.models.scan",
        "ai_model_manager.models.show",
        "ai_model_manager.preferences.create",
        "ai_model_manager.preferences.delete",
        "ai_model_manager.preferences.edit",
        "ai_model_manager.preferences.list",
        "contacts_and_discussions.chat_targets.create",
        "contacts_and_discussions.chat_targets.delete",
        "contacts_and_discussions.chat_targets.edit",
        "contacts_and_discussions.chat_targets.list",
        "contacts_and_discussions.discussions.create",
        "contacts_and_discussions.discussions.delete",
        "contacts_and_discussions.discussions.edit",
        "contacts_and_discussions.discussions.list",
        "contacts_and_discussions.summaries.create",
        "contacts_and_discussions.summaries.delete",
        "contacts_and_discussions.summaries.edit",
        "contacts_and_discussions.summaries.list",
        "contacts_and_discussions.topics.assess_transition",
        "contacts_and_discussions.topics.create",
        "contacts_and_discussions.topics.delete",
        "contacts_and_discussions.topics.edit",
        "contacts_and_discussions.topics.list",
        "contacts_and_discussions.topics.summarize",
        "contacts_and_discussions.turns.create",
        "contacts_and_discussions.turns.delete",
        "contacts_and_discussions.turns.edit",
        "contacts_and_discussions.turns.list",
        "ipe.calendar_event.create",
        "ipe.calendar_event.delete",
        "ipe.calendar_event.edit",
        "ipe.calendar_event.list",
        "ipe.habit.create",
        "ipe.habit.delete",
        "ipe.habit.edit",
        "ipe.habit.list",
        "ipe.idea.create",
        "ipe.idea.delete",
        "ipe.idea.edit",
        "ipe.idea.list",
        "ipe.project.create",
        "ipe.project.delete",
        "ipe.project.edit",
        "ipe.project.list",
        "ipe.task.create",
        "ipe.task.delete",
        "ipe.task.edit",
        "ipe.task.list",
        "worksim.org_chart_node.create",
        "worksim.org_chart_node.delete",
        "worksim.org_chart_node.edit",
        "worksim.org_chart_node.list",
    ]
    assert [view.view_id for view in registry.list_views()] == [
        "agent_alarms.alarms.view",
        "agent_config.agent_config.view",
        "agent_loops.contacts.view",
        "agent_loops.knowledge.view",
        "agent_loops.tasks.view",
        "agent_loops.workspace.view",
        "ai_host_management.hosts.view",
        "ai_host_management.resources.view",
        "ai_model_manager.models.view",
        "ai_model_manager.preferences.view",
        "contacts_and_discussions.chat_targets.view",
        "ipe.calendar_event.view",
        "ipe.habit.view",
        "ipe.idea.view",
        "ipe.project.view",
        "ipe.task.view",
        "worksim.org_chart_node.view",
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
        "agent_alarms",
        "agent_config",
        "agent_loops",
        "ai_host_management",
        "ai_model_executor",
        "ai_model_manager",
        "contacts_and_discussions",
        "ipe",
        "source_inspection",
        "worksim",
    ]
