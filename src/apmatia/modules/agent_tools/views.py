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

from .models import ToolDefinition

# Agent Tools form fields
_TOOL_FORM_FIELDS = (
    ViewComponent(
        component_id="tool-name-field",
        component_type="field",
        properties={"label": "Name", "field_type": "text", "required": True, "placeholder": "Tool name"},
    ),
    ViewComponent(
        component_id="tool-description-field",
        component_type="field",
        properties={"label": "Description", "field_type": "textarea", "placeholder": "What this tool does"},
    ),
    ViewComponent(
        component_id="tool-provider-id-field",
        component_type="field",
        properties={"label": "Provider ID", "field_type": "text", "required": True, "placeholder": "provider.tool_name"},
    ),
    ViewComponent(
        component_id="tool-enabled-field",
        component_type="field",
        properties={"label": "Enabled", "field_type": "checkbox", "default": True},
    ),
    ViewComponent(
        component_id="tool-confirmation-required-field",
        component_type="field",
        properties={"label": "Confirmation required", "field_type": "checkbox", "default": False},
    ),
    ViewComponent(
        component_id="tool-read-only-field",
        component_type="field",
        properties={"label": "Read only", "field_type": "checkbox", "default": False},
    ),
    ViewComponent(
        component_id="tool-input-schema-field",
        component_type="field",
        properties={"label": "Input schema", "field_type": "textarea", "default": "{}", "help_text": "JSON object"},
    ),
    ViewComponent(
        component_id="tool-output-schema-field",
        component_type="field",
        properties={"label": "Output schema", "field_type": "textarea", "default": "{}", "help_text": "JSON object"},
    ),
    ViewComponent(
        component_id="tool-metadata-field",
        component_type="field",
        properties={"label": "Metadata", "field_type": "textarea", "default": "{}", "help_text": "JSON object"},
    ),
)

# Agent Tools view presentation tree
_AGENT_TOOLS_PRESENTATION = ViewComponent(
    component_id="agent-tools-page",
    component_type="page",
    properties={"title": "Agent Tools", "caption": "Create and update tool definitions used by Apmatia agents."},
    children=(
        ViewComponent(
            component_id="agent-tools-collection",
            component_type="collection",
            binding=ViewBinding(source="agent_tools", path="items"),
            children=(
                ViewComponent(
                    component_id="agent-tools-table",
                    component_type="table",
                    properties={
                        "columns": [
                            {"key": "name", "label": "Name"},
                            {"key": "provider_id", "label": "Provider ID"},
                            {"key": "enabled", "label": "Enabled"},
                            {"key": "confirmation_required", "label": "Confirmation"},
                            {"key": "read_only", "label": "Read only"},
                        ],
                    },
                    action_keys=("edit",),
                ),
            ),
        ),
        ViewComponent(
            component_id="agent-tools-view-actions",
            component_type="actions",
            properties={"label": "Create agent tool"},
            action_keys=("create",),
        ),
        ViewComponent(
            component_id="create-tool-form",
            component_type="form",
            properties={"title": "Create agent tool", "submit_label": "Create agent tool"},
            children=_TOOL_FORM_FIELDS,
            action_keys=("create",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_create_form")),
        ),
        ViewComponent(
            component_id="edit-tool-form",
            component_type="form",
            properties={"title": "Edit agent tool", "submit_label": "Save agent tool"},
            children=_TOOL_FORM_FIELDS,
            action_keys=("edit",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_edit_form")),
        ),
    ),
)

# Agent Tools view data sources
_AGENT_TOOLS_DATA_SOURCES = (
    ViewDataSource(
        key="agent_tools",
        kind="collection",
        operation="agent_tools:list",
        parameters={"label_keys": ["name"], "value_key": "id", "default_label": "Unnamed tool", "include_empty": True},
    ),
)

# Agent Tools view state
_AGENT_TOOLS_STATE = (
    ViewStateDefinition(key="selected_tool_id", value_type="string", default=""),
    ViewStateDefinition(key="show_create_form", value_type="boolean", default=False),
    ViewStateDefinition(key="show_edit_form", value_type="boolean", default=False),
    ViewStateDefinition(key="edit_target_id", value_type="string", default=""),
)

# Agent Tools view actions
_AGENT_TOOLS_ACTIONS = (
    ViewAction(
        key="create",
        intent="create",
        label="Create agent tool",
        scope="view",
        style="primary",
        operation="agent_tools:create",
        payload={"command_id": "agent_tools.create"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_create_form", value=False),
            ViewEffect(effect_type="refresh_view", target="agent_tools.agent_tools.view"),
            ViewEffect(effect_type="show_notification", value="Tool created successfully"),
        ),
    ),
    ViewAction(
        key="edit",
        intent="edit",
        label="Edit",
        scope="item",
        operation="agent_tools:edit",
        payload={"command_id": "agent_tools.edit"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_edit_form", value=False),
            ViewEffect(effect_type="set_state", target="selected_tool_id", value="$item.id"),
            ViewEffect(effect_type="refresh_view", target="agent_tools.agent_tools.view"),
        ),
    ),
)

# Agent Tools view effects
_AGENT_TOOLS_EFFECTS = ()

# Agent Tools view refresh policy
_AGENT_TOOLS_REFRESH_POLICY = ViewRefreshPolicy(mode="on_intent")


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="agent_tools",
        action_id="agent_tools.agent_tools",
        view_id="agent_tools.agent_tools.view",
        name="Agent Tools",
        description="Create and update tool definitions used by Apmatia agents.",
        metadata={
            "view_contract_ready": True,
            "object_type": "agent_tool",
            "singular_label": "Agent Tool",
            "plural_label": "Agent Tools",
            "empty_state": "No agent tools are available yet.",
            "presentation": _AGENT_TOOLS_PRESENTATION,
            "data_sources": _AGENT_TOOLS_DATA_SOURCES,
            "state": _AGENT_TOOLS_STATE,
            "actions": _AGENT_TOOLS_ACTIONS,
            "effects": _AGENT_TOOLS_EFFECTS,
            "refresh_policy": _AGENT_TOOLS_REFRESH_POLICY,
        },
    ),
)
