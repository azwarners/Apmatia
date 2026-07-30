from __future__ import annotations

from datetime import datetime

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

from .models import AgentAlarm

# Alarm form fields (shared between create and edit)
_ALARM_FORM_FIELDS = (
    ViewComponent(
        component_id="alarm-name-field",
        component_type="field",
        properties={"label": "Alarm name", "field_type": "text", "placeholder": "Nightly summary"},
    ),
    ViewComponent(
        component_id="alarm-agent-id-field",
        component_type="field",
        properties={"label": "Agent", "field_type": "select", "binding_source": "agents", "binding_path": "items", "help_text": "Choose the agent that will execute this alarm."},
    ),
    ViewComponent(
        component_id="alarm-prompt-field",
        component_type="field",
        properties={"label": "Prompt", "field_type": "textarea", "placeholder": "Review the last 24 hours and prepare a concise report.", "help_text": "The prompt the agent should execute when the alarm fires."},
    ),
    ViewComponent(
        component_id="alarm-model-id-field",
        component_type="field",
        properties={"label": "Model", "field_type": "select", "binding_source": "model_configs", "binding_path": "items", "help_text": "Choose the model alias to use for this alarm."},
    ),
    ViewComponent(
        component_id="alarm-scheduled-start-date-field",
        component_type="field",
        properties={"label": "Scheduled date", "field_type": "date", "help_text": "Pick the day the alarm should start."},
    ),
    ViewComponent(
        component_id="alarm-scheduled-start-time-field",
        component_type="field",
        properties={"label": "Scheduled time", "field_type": "time", "help_text": "Pick the time of day the alarm should start."},
    ),
    ViewComponent(
        component_id="alarm-enabled-field",
        component_type="field",
        properties={"label": "Enabled", "field_type": "checkbox", "default": True},
    ),
)

# Agent Alarms view presentation tree
_AGENT_ALARMS_PRESENTATION = ViewComponent(
    component_id="agent-alarms-page",
    component_type="page",
    properties={"title": "Agent Alarms", "caption": "Create alarms that wake an agent up at a specific time and hand the work to Agent Loops."},
    children=(
        ViewComponent(
            component_id="agent-alarms-collection",
            component_type="collection",
            binding=ViewBinding(source="alarms", path="items"),
            children=(
                ViewComponent(
                    component_id="agent-alarms-table",
                    component_type="table",
                    properties={
                        "columns": [
                            {"key": "name", "label": "Alarm"},
                            {"key": "agent_name", "label": "Agent"},
                            {"key": "model_name", "label": "Model"},
                            {"key": "scheduled_start_time_display", "label": "Scheduled"},
                            {"key": "status_label", "label": "Status"},
                            {"key": "enabled_label", "label": "Enabled"},
                            {"key": "result_summary", "label": "Result"},
                            {"key": "error_summary", "label": "Error"},
                        ],
                    },
                    action_keys=("edit", "delete"),
                ),
            ),
        ),
        ViewComponent(
            component_id="agent-alarms-view-actions",
            component_type="actions",
            properties={"label": "Create alarm"},
            action_keys=("create",),
        ),
        ViewComponent(
            component_id="create-alarm-form",
            component_type="form",
            properties={"title": "Create alarm", "submit_label": "Create alarm"},
            children=_ALARM_FORM_FIELDS,
            action_keys=("create",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_create_form")),
        ),
        ViewComponent(
            component_id="edit-alarm-form",
            component_type="form",
            properties={"title": "Edit alarm", "submit_label": "Save changes"},
            children=_ALARM_FORM_FIELDS,
            action_keys=("edit",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_edit_form")),
        ),
    ),
)

# Agent Alarms view data sources
_AGENT_ALARMS_DATA_SOURCES = (
    ViewDataSource(
        key="alarms",
        kind="collection",
        operation="agent_alarms:list",
        parameters={"label_keys": ["name"], "value_key": "id", "default_label": "Unnamed alarm", "include_empty": True},
    ),
    ViewDataSource(
        key="agents",
        kind="collection",
        operation="agents:list",
        parameters={"label_keys": ["name"], "value_key": "id", "default_label": "Unnamed agent"},
    ),
    ViewDataSource(
        key="model_configs",
        kind="collection",
        operation="model_configs:list",
        parameters={"label_keys": ["user_alias", "name", "provider_name"], "value_key": "id", "default_label": "Unnamed model"},
    ),
)

# Agent Alarms view state
_AGENT_ALARMS_STATE = (
    ViewStateDefinition(key="selected_alarm_id", value_type="string", default=""),
    ViewStateDefinition(key="show_create_form", value_type="boolean", default=False),
    ViewStateDefinition(key="show_edit_form", value_type="boolean", default=False),
    ViewStateDefinition(key="edit_target_id", value_type="string", default=""),
)

# Agent Alarms view actions
_AGENT_ALARMS_ACTIONS = (
    ViewAction(
        key="create",
        intent="create",
        label="Create alarm",
        scope="view",
        style="primary",
        operation="agent_alarms:create",
        payload={"command_id": "agent_alarms.create"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_create_form", value=False),
            ViewEffect(effect_type="refresh_view", target="agent_alarms.alarms.view"),
            ViewEffect(effect_type="show_notification", value="Alarm created successfully"),
        ),
    ),
    ViewAction(
        key="edit",
        intent="edit",
        label="Edit",
        scope="item",
        style="secondary",
        operation="agent_alarms:edit",
        payload={"command_id": "agent_alarms.edit"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_edit_form", value=False),
            ViewEffect(effect_type="set_state", target="selected_alarm_id", value="$item.id"),
            ViewEffect(effect_type="refresh_view", target="agent_alarms.alarms.view"),
        ),
    ),
    ViewAction(
        key="delete",
        intent="delete",
        label="Delete",
        scope="item",
        style="secondary",
        operation="agent_alarms:delete",
        payload={"command_id": "agent_alarms.delete"},
        confirmation=True,
        success_effects=(
            ViewEffect(effect_type="set_state", target="selected_alarm_id", value=""),
            ViewEffect(effect_type="refresh_view", target="agent_alarms.alarms.view"),
            ViewEffect(effect_type="show_notification", value="Alarm deleted"),
        ),
    ),
)

# Agent Alarms view effects
_AGENT_ALARMS_EFFECTS = ()

# Agent Alarms view refresh policy
_AGENT_ALARMS_REFRESH_POLICY = ViewRefreshPolicy(mode="on_intent")


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="agent_alarms",
        action_id="agent_alarms.alarms",
        view_id="agent_alarms.alarms.view",
        name="Agent Alarms",
        description="Schedule autonomous alarm-style agent runs.",
        metadata={
            "view_contract_ready": True,
            "object_type": "alarm",
            "singular_label": "Alarm",
            "plural_label": "Alarms",
            "empty_state": "No alarms have been created yet.",
            "presentation": _AGENT_ALARMS_PRESENTATION,
            "data_sources": _AGENT_ALARMS_DATA_SOURCES,
            "state": _AGENT_ALARMS_STATE,
            "actions": _AGENT_ALARMS_ACTIONS,
            "effects": _AGENT_ALARMS_EFFECTS,
            "refresh_policy": _AGENT_ALARMS_REFRESH_POLICY,
        },
    ),
)
