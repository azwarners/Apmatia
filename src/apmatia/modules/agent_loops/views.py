from __future__ import annotations

from apmatia.core.registry import ViewContribution
from apmatia.core.view_contract.models import (
    ViewComponent,
    ViewBinding,
    ViewCondition,
    ViewDataSource,
    ViewStateDefinition,
    ViewAction,
    ViewEffect,
    ViewRefreshPolicy,
)


# Agent Loops view presentation tree
_AGENT_LOOPS_PRESENTATION = ViewComponent(
    component_id="agent-loops-page",
    component_type="page",
    properties={"title": "Agent Loops", "caption": "Contact selection, task execution, workspace, and knowledge management."},
    children=(
        ViewComponent(
            component_id="contact-selection-panel",
            component_type="panel",
            properties={"title": "Contacts"},
            children=(
                ViewComponent(
                    component_id="contact-nav",
                    component_type="navigation",
                    properties={"binding_source": "contacts", "binding_path": "items"},
                    children=(
                        ViewComponent(
                            component_id="contact-item",
                            component_type="card",
                            properties={"binding_source": "contacts", "binding_path": "items"},
                            children=(
                                ViewComponent(
                                    component_id="contact-label",
                                    component_type="text",
                                    properties={"binding_source": "contacts", "binding_path": "title"},
                                ),
                                ViewComponent(
                                    component_id="contact-task-count",
                                    component_type="status",
                                    properties={"binding_source": "contacts", "binding_path": "task_count"},
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        ViewComponent(
            component_id="task-tabs",
            component_type="tabs",
            properties={"tabs": ("Current Task", "Task History", "Workspace", "Knowledge")},
            children=(
                ViewComponent(
                    component_id="current-task-tab",
                    component_type="panel",
                    properties={"title": "Current Task"},
                    children=(
                        ViewComponent(
                            component_id="new-task-form",
                            component_type="form",
                            properties={"title": "New Task", "binding_source": "agents", "binding_path": "items"},
                            children=(
                                ViewComponent(
                                    component_id="task-title-field",
                                    component_type="field",
                                    properties={"label": "Task title", "field_type": "text"},
                                ),
                                ViewComponent(
                                    component_id="task-prompt-field",
                                    component_type="field",
                                    properties={"label": "Prompt", "field_type": "textarea"},
                                ),
                                ViewComponent(
                                    component_id="max-turns-field",
                                    component_type="field",
                                    properties={"label": "Max turns", "field_type": "number", "min_value": 1, "default": 10},
                                ),
                                ViewComponent(
                                    component_id="launch-action",
                                    component_type="actions",
                                    properties={"label": "Launch task"},
                                    action_keys=("launch_task",),
                                ),
                            ),
                        ),
                        ViewComponent(
                            component_id="current-task-output",
                            component_type="terminal",
                            properties={"binding_source": "current_task", "binding_path": "output"},
                        ),
                        ViewComponent(
                            component_id="current-task-checklist",
                            component_type="checklist",
                            properties={"binding_source": "current_task", "binding_path": "checklist"},
                        ),
                        ViewComponent(
                            component_id="current-task-progress",
                            component_type="progress",
                            properties={"binding_source": "current_task", "binding_path": "progress"},
                        ),
                    ),
                ),
                ViewComponent(
                    component_id="task-history-tab",
                    component_type="panel",
                    properties={"title": "Task History"},
                    children=(
                        ViewComponent(
                            component_id="task-history-collection",
                            component_type="collection",
                            binding=ViewBinding(source="tasks", path="items"),
                            properties={"binding_source": "tasks", "binding_path": "items"},
                            children=(
                                ViewComponent(
                                    component_id="task-history-card",
                                    component_type="card",
                                    properties={"binding_source": "tasks", "binding_path": "items"},
                                    children=(
                                        ViewComponent(
                                            component_id="task-status-banner",
                                            component_type="status",
                                            properties={"binding_source": "tasks", "binding_path": "status"},
                                        ),
                                        ViewComponent(
                                            component_id="stop-task-action",
                                            component_type="actions",
                                            properties={"label": "Stop task"},
                                            action_keys=("stop_task",),
                                            visible_when=ViewCondition(operator="in", operands=("$state.task_status", ("running", "stopping"))),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                ViewComponent(
                    component_id="workspace-tab",
                    component_type="panel",
                    properties={"title": "Workspace"},
                    children=(
                        ViewComponent(
                            component_id="workspace-tree",
                            component_type="tree",
                            binding=ViewBinding(source="workspace", path="items"),
                            properties={"binding_source": "workspace", "binding_path": "items"},
                        ),
                    ),
                ),
                ViewComponent(
                    component_id="knowledge-tab",
                    component_type="panel",
                    properties={"title": "Knowledge"},
                    children=(
                        ViewComponent(
                            component_id="knowledge-tree",
                            component_type="tree",
                            binding=ViewBinding(source="knowledge", path="items"),
                            properties={"binding_source": "knowledge", "binding_path": "items"},
                        ),
                    ),
                ),
            ),
        ),
    ),
)

# Agent Loops data sources
_AGENT_LOOPS_DATA_SOURCES = (
    ViewDataSource(
        key="contacts",
        kind="collection",
        operation="list_contacts",
        item_key="id",
        empty_text="No contacts available.",
    ),
    ViewDataSource(
        key="tasks",
        kind="collection",
        operation="list_tasks",
        depends_on=("contacts",),
        item_key="task_id",
        empty_text="No tasks recorded.",
    ),
    ViewDataSource(
        key="current_task",
        kind="singleton",
        operation="get_current_task",
        depends_on=("contacts", "tasks"),
    ),
    ViewDataSource(
        key="workspace",
        kind="tree",
        operation="list_workspace_files",
        depends_on=("contacts",),
        item_key="path",
        empty_text="No workspace files.",
    ),
    ViewDataSource(
        key="knowledge",
        kind="tree",
        operation="list_knowledge_files",
        depends_on=("contacts",),
        item_key="path",
        empty_text="No knowledge files.",
    ),
    ViewDataSource(
        key="agents",
        kind="collection",
        operation="list_agents",
        item_key="id",
        empty_text="No agents available.",
    ),
)

# Agent Loops state definitions
_AGENT_LOOPS_STATE = (
    ViewStateDefinition(
        key="selected_contact_id",
        value_type="string",
        scope="session",
        default=None,
    ),
    ViewStateDefinition(
        key="selected_task_id",
        value_type="string",
        scope="view",
        default=None,
    ),
    ViewStateDefinition(
        key="task_status",
        value_type="string",
        scope="view",
        default="unknown",
    ),
    ViewStateDefinition(
        key="is_running",
        value_type="boolean",
        scope="view",
        default=False,
    ),
    ViewStateDefinition(
        key="selected_tab",
        value_type="string",
        scope="view",
        default="Current Task",
    ),
)

# Agent Loops actions
_AGENT_LOOPS_ACTIONS = (
    ViewAction(
        key="launch_task",
        intent="start_task",
        label="Launch task",
        scope="form",
        command_id="agent_loops.start",
        payload={"contact_id": "$state.selected_contact_id", "prompt": "$state.task_prompt", "title": "$state.task_title", "max_iterations": "$state.max_turns"},
        confirmation=False,
        prevent_duplicate_submission=True,
        success_effects=(
            ViewEffect(effect_type="set_state", target="selected_task_id", value="$result.task_id"),
            ViewEffect(effect_type="set_state", target="is_running", value=True),
            ViewEffect(effect_type="refresh_source", target="tasks"),
            ViewEffect(effect_type="show_notification", value="Task started."),
        ),
    ),
    ViewAction(
        key="stop_task",
        intent="stop_task",
        label="Stop task",
        scope="item",
        command_id="agent_loops.stop",
        payload={"task_id": "$item.task_id"},
        confirmation=True,
        prevent_duplicate_submission=False,
        success_effects=(
            ViewEffect(effect_type="set_state", target="is_running", value=False),
            ViewEffect(effect_type="refresh_source", target="current_task"),
            ViewEffect(effect_type="refresh_source", target="tasks"),
            ViewEffect(effect_type="show_notification", value="Task stopping."),
        ),
    ),
    ViewAction(
        key="select_contact",
        intent="select_contact",
        label="Select",
        scope="navigation",
        command_id="agent_loops.contact.select",
        payload={"contact_id": "$item.id"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="selected_contact_id", value="$item.id"),
            ViewEffect(effect_type="refresh_source", target="tasks"),
        ),
    ),
)

# Agent Loops effects
_AGENT_LOOPS_EFFECTS = (
    ViewEffect(effect_type="start_polling", target="current_task"),
    ViewEffect(effect_type="stop_polling", target="current_task"),
    ViewEffect(effect_type="navigate", target="agent_loops.contacts.view"),
    ViewEffect(effect_type="show_notification", target="notification"),
)

# Agent Loops refresh policy
_AGENT_LOOPS_REFRESH_POLICY = ViewRefreshPolicy(
    mode="poll",
    interval_seconds=1.0,
    cursor_key="cursor",
    generation_key="generation",
    update_strategy="append",
    reject_stale=True,
    stop_when=ViewCondition(operator="equals", operands=(False, "$state.is_running")),
)

# Agent Loops capabilities
_AGENT_LOOPS_CAPABILITIES = (
    "can_start_task",
    "can_stop_task",
    "can_select_contact",
    "can_view_workspace",
    "can_view_knowledge",
)


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="agent_loops",
        action_id="agent_loops.contacts",
        view_id="agent_loops.contacts.view",
        name="Contacts",
        description="Agents and groups that can own loop tasks.",
        metadata={"object_type": "contact"},
    ),
    ViewContribution(
        module_id="agent_loops",
        action_id="agent_loops.tasks",
        view_id="agent_loops.tasks.view",
        name="Tasks",
        description="Recorded loop executions.",
        metadata={"object_type": "run"},
    ),
    ViewContribution(
        module_id="agent_loops",
        action_id="agent_loops.workspace",
        view_id="agent_loops.workspace.view",
        name="Workspace",
        description="Workspace files for the selected contact.",
        metadata={"object_type": "workspace"},
    ),
    ViewContribution(
        module_id="agent_loops",
        action_id="agent_loops.knowledge",
        view_id="agent_loops.knowledge.view",
        name="Knowledge",
        description="Knowledge files for the selected contact.",
        metadata={"object_type": "knowledge"},
    ),
    ViewContribution(
        module_id="agent_loops",
        action_id="agent_loops.loops",
        view_id="agent_loops.loops.view",
        name="Agent Loops View",
        description="Contact selection, task execution, workspace, and knowledge management.",
        metadata={
            "schema_version": 1,
            "title": "Agent Loops",
            "description": "Interactive task execution interface with contact selection, live output, checklist progress, and file trees.",
            "presentation": _AGENT_LOOPS_PRESENTATION,
            "data_sources": _AGENT_LOOPS_DATA_SOURCES,
            "state": _AGENT_LOOPS_STATE,
            "actions": _AGENT_LOOPS_ACTIONS,
            "effects": _AGENT_LOOPS_EFFECTS,
            "refresh_policy": _AGENT_LOOPS_REFRESH_POLICY,
            "capabilities": _AGENT_LOOPS_CAPABILITIES,
            "required_renderer_capabilities": ("terminal", "checklist", "progress", "tree"),
        },
    ),
)
