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

# Agent Config form fields
_AGENT_CONFIG_FORM_FIELDS = (
    ViewComponent(
        component_id="agent-config-workspace-root-field",
        component_type="field",
        properties={"label": "Workspace root", "field_type": "text", "help_text": "Use an absolute path writable by the Apmatia process."},
    ),
    ViewComponent(
        component_id="agent-config-knowledge-root-field",
        component_type="field",
        properties={"label": "Knowledge root", "field_type": "text", "help_text": "Knowledge roots can be shared across agents."},
    ),
)

# Agent Config view presentation tree
_AGENT_CONFIG_PRESENTATION = ViewComponent(
    component_id="agent-config-page",
    component_type="page",
    properties={"title": "Agent Config", "caption": "Choose an agent by name, then update its workspace and knowledge roots. Knowledge roots may be shared across agents; workspace roots usually should not be."},
    children=(
        ViewComponent(
            component_id="agent-config-collection",
            component_type="collection",
            binding=ViewBinding(source="agents", path="items"),
            children=(
                ViewComponent(
                    component_id="agent-config-table",
                    component_type="table",
                    properties={
                        "columns": [
                            {"key": "name", "label": "Agent"},
                            {"key": "workspace_root", "label": "Workspace Root"},
                            {"key": "knowledge_root", "label": "Knowledge Root"},
                            {"key": "workspace_root_status", "label": "Workspace Status"},
                            {"key": "knowledge_root_status", "label": "Knowledge Status"},
                        ],
                    },
                    action_keys=("edit",),
                ),
            ),
        ),
        ViewComponent(
            component_id="agent-config-edit-form",
            component_type="form",
            properties={"title": "Edit agent roots", "submit_label": "Save configuration"},
            children=_AGENT_CONFIG_FORM_FIELDS,
            action_keys=("edit",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_edit_form")),
        ),
    ),
)

# Agent Config view data sources
_AGENT_CONFIG_DATA_SOURCES = (
    ViewDataSource(
        key="agents",
        kind="collection",
        operation="agents:list",
        parameters={"label_keys": ["name"], "value_key": "id", "default_label": "Unnamed agent", "include_empty": True},
    ),
)

# Agent Config view state
_AGENT_CONFIG_STATE = (
    ViewStateDefinition(key="selected_agent_id", value_type="string", default=""),
    ViewStateDefinition(key="show_edit_form", value_type="boolean", default=False),
    ViewStateDefinition(key="edit_target_id", value_type="string", default=""),
)

# Agent Config view actions
_AGENT_CONFIG_ACTIONS = (
    ViewAction(
        key="edit",
        intent="edit",
        label="Edit roots",
        scope="item",
        style="secondary",
        operation="agent_config:save",
        payload={"command_id": "agent_config.save"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_edit_form", value=False),
            ViewEffect(effect_type="set_state", target="selected_agent_id", value="$item.id"),
            ViewEffect(effect_type="refresh_view", target="agent_config.agent_config.view"),
            ViewEffect(effect_type="show_notification", value="Agent configuration saved"),
        ),
    ),
)

# Agent Config view effects
_AGENT_CONFIG_EFFECTS = ()

# Agent Config view refresh policy
_AGENT_CONFIG_REFRESH_POLICY = ViewRefreshPolicy(mode="on_intent")


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="agent_config",
        action_id="agent_config.agent_config",
        view_id="agent_config.agent_config.view",
        name="Agent Config",
        description="Select an agent and configure its workspace and knowledge roots.",
        metadata={
            "view_contract_ready": True,
            "object_type": "agent_config",
            "empty_state": "No agents have been created yet.",
            "presentation": _AGENT_CONFIG_PRESENTATION,
            "data_sources": _AGENT_CONFIG_DATA_SOURCES,
            "state": _AGENT_CONFIG_STATE,
            "actions": _AGENT_CONFIG_ACTIONS,
            "effects": _AGENT_CONFIG_EFFECTS,
            "refresh_policy": _AGENT_CONFIG_REFRESH_POLICY,
        },
    ),
)
