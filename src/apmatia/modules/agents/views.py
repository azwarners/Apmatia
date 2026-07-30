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


# Agent edit form fields (shared between create and edit)
_AGENT_FORM_FIELDS = (
    ViewComponent(
        component_id="agent-name-field",
        component_type="field",
        properties={"label": "Name", "field_type": "text", "required": True},
    ),
    ViewComponent(
        component_id="agent-owner-user-id-field",
        component_type="field",
        properties={"label": "Owner user ID", "field_type": "number"},
    ),
    ViewComponent(
        component_id="agent-owner-group-id-field",
        component_type="field",
        properties={"label": "Owner group ID", "field_type": "number"},
    ),
    ViewComponent(
        component_id="agent-memory-id-field",
        component_type="field",
        properties={"label": "Memory ID", "field_type": "number", "default": 0},
    ),
    ViewComponent(
        component_id="agent-default-model-id-field",
        component_type="field",
        properties={"label": "Default model", "field_type": "select", "binding_source": "model_configs", "binding_path": "items"},
    ),
    ViewComponent(
        component_id="agent-active-model-id-field",
        component_type="field",
        properties={"label": "Active model", "field_type": "select", "binding_source": "model_configs", "binding_path": "items"},
    ),
    ViewComponent(
        component_id="agent-workspace-root-field",
        component_type="field",
        properties={"label": "Workspace root", "field_type": "text"},
    ),
    ViewComponent(
        component_id="agent-knowledge-root-field",
        component_type="field",
        properties={"label": "Knowledge root", "field_type": "text"},
    ),
    ViewComponent(
        component_id="agent-rag-root-ids-field",
        component_type="field",
        properties={"label": "RAG root IDs (JSON)", "field_type": "textarea", "default": "[]"},
    ),
    ViewComponent(
        component_id="agent-tool-ids-field",
        component_type="field",
        properties={"label": "Tool IDs (JSON)", "field_type": "textarea", "default": "[]"},
    ),
    ViewComponent(
        component_id="agent-metadata-field",
        component_type="field",
        properties={"label": "Metadata (JSON)", "field_type": "textarea", "default": "{}"},
    ),
    ViewComponent(
        component_id="agent-personality-field",
        component_type="field",
        properties={"label": "Personality", "field_type": "textarea", "section": "Prompt"},
    ),
    ViewComponent(
        component_id="agent-skills-field",
        component_type="field",
        properties={"label": "Skills", "field_type": "textarea", "section": "Prompt"},
    ),
    ViewComponent(
        component_id="agent-purpose-field",
        component_type="field",
        properties={"label": "Purpose / Mission", "field_type": "textarea", "section": "Prompt"},
    ),
    ViewComponent(
        component_id="agent-backstory-field",
        component_type="field",
        properties={"label": "Backstory", "field_type": "textarea", "section": "Prompt"},
    ),
    ViewComponent(
        component_id="agent-communication-style-field",
        component_type="field",
        properties={"label": "Communication style", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-operating-principles-field",
        component_type="field",
        properties={"label": "Operating principles", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-autonomy-level-field",
        component_type="field",
        properties={"label": "Autonomy level", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-decision-making-style-field",
        component_type="field",
        properties={"label": "Decision making style", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-memory-policy-field",
        component_type="field",
        properties={"label": "Memory policy", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-domain-priorities-field",
        component_type="field",
        properties={"label": "Domain priorities", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-relationship-to-user-field",
        component_type="field",
        properties={"label": "Relationship to user", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-tool-use-policy-field",
        component_type="field",
        properties={"label": "Tool use policy", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-capability-boundaries-field",
        component_type="field",
        properties={"label": "Capability boundaries", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-output-preferences-field",
        component_type="field",
        properties={"label": "Output preferences", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-safety-ethics-field",
        component_type="field",
        properties={"label": "Safety ethics", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-selfhood-truthfulness-field",
        component_type="field",
        properties={"label": "Selfhood truthfulness", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-conflict-resolution-rules-field",
        component_type="field",
        properties={"label": "Conflict resolution rules", "field_type": "textarea", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-use-raw-prompt-override-field",
        component_type="field",
        properties={"label": "Use raw prompt override", "field_type": "checkbox", "section": "Advanced prompt"},
    ),
    ViewComponent(
        component_id="agent-raw-prompt-override-field",
        component_type="field",
        properties={"label": "Raw prompt override", "field_type": "textarea", "section": "Advanced prompt"},
    ),
)

# Agents view presentation tree
_AGENTS_PRESENTATION = ViewComponent(
    component_id="agents-page",
    component_type="page",
    properties={"title": "Agents", "caption": "Create, edit, clone, and remove agents through the stable module API."},
    children=(
        ViewComponent(
            component_id="agents-collection",
            component_type="collection",
            binding=ViewBinding(source="agents", path="items"),
            children=(
                ViewComponent(
                    component_id="agents-table",
                    component_type="table",
                    properties={
                        "columns": [
                            {"key": "name", "label": "Name"},
                            {"key": "owner_user_id", "label": "Owner User"},
                            {"key": "owner_group_id", "label": "Owner Group"},
                            {"key": "default_model_id", "label": "Default Model"},
                            {"key": "workspace_root", "label": "Workspace"},
                            {"key": "knowledge_root", "label": "Knowledge"},
                        ],
                    },
                    action_keys=("edit", "clone", "delete"),
                ),
            ),
        ),
        ViewComponent(
            component_id="agents-view-actions",
            component_type="actions",
            properties={"label": "Create agent"},
            action_keys=("create",),
        ),
        ViewComponent(
            component_id="create-agent-form",
            component_type="form",
            properties={"title": "Create agent", "submit_label": "Create agent"},
            children=_AGENT_FORM_FIELDS,
            action_keys=("create",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_create_form")),
        ),
        ViewComponent(
            component_id="edit-agent-form",
            component_type="form",
            properties={"title": "Edit agent", "submit_label": "Save agent"},
            children=_AGENT_FORM_FIELDS,
            action_keys=("edit",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_edit_form")),
        ),
    ),
)

# Agents view data sources
_AGENTS_DATA_SOURCES = (
    ViewDataSource(
        key="agents",
        kind="collection",
        operation="agents:list",
        parameters={"label_keys": ["name"], "value_key": "id", "default_label": "Unnamed agent", "include_empty": True},
    ),
    ViewDataSource(
        key="model_configs",
        kind="collection",
        operation="model_configs:list",
        parameters={"label_keys": ["user_alias", "name"], "value_key": "id", "default_label": "Unnamed model", "include_empty": True},
    ),
)

# Agents view state
_AGENTS_STATE = (
    ViewStateDefinition(key="selected_agent_id", value_type="string", default=""),
    ViewStateDefinition(key="show_create_form", value_type="boolean", default=False),
    ViewStateDefinition(key="show_edit_form", value_type="boolean", default=False),
    ViewStateDefinition(key="edit_target_id", value_type="string", default=""),
)

# Agents view actions
_AGENTS_ACTIONS = (
    ViewAction(
        key="create",
        intent="create",
        label="Create agent",
        scope="view",
        style="primary",
        operation="agents:create",
        payload={"command_id": "agents.create"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_create_form", value=False),
            ViewEffect(effect_type="refresh_view", target="agents.agents.view"),
            ViewEffect(effect_type="show_notification", value="Agent created successfully"),
        ),
    ),
    ViewAction(
        key="edit",
        intent="edit",
        label="Edit",
        scope="item",
        operation="agents:edit",
        payload={"command_id": "agents.edit"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_edit_form", value=False),
            ViewEffect(effect_type="set_state", target="selected_agent_id", value="$item.id"),
            ViewEffect(effect_type="refresh_view", target="agents.agents.view"),
        ),
    ),
    ViewAction(
        key="clone",
        intent="clone",
        label="Clone",
        scope="item",
        operation="agents:clone",
        payload={"command_id": "agents.clone"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_create_form", value=True),
            ViewEffect(effect_type="set_state", target="edit_target_id", value="$item.id"),
        ),
    ),
    ViewAction(
        key="delete",
        intent="delete",
        label="Delete",
        scope="item",
        style="danger",
        operation="agents:delete",
        payload={"command_id": "agents.delete"},
        confirmation=True,
        success_effects=(
            ViewEffect(effect_type="set_state", target="selected_agent_id", value=""),
            ViewEffect(effect_type="refresh_view", target="agents.agents.view"),
            ViewEffect(effect_type="show_notification", value="Agent deleted"),
        ),
    ),
)

# Agents view effects
_AGENTS_EFFECTS = ()

# Agents view refresh policy
_AGENTS_REFRESH_POLICY = ViewRefreshPolicy(mode="on_intent")


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="agents",
        action_id="agents.agents",
        view_id="agents.agents.view",
        name="Agents",
        description="Create, edit, clone, and remove agents through the Apmatia module API.",
        metadata={
            "view_contract_ready": True,
            "object_type": "agent",
            "singular_label": "Agent",
            "plural_label": "Agents",
            "empty_state": "No agents have been created yet.",
            "presentation": _AGENTS_PRESENTATION,
            "data_sources": _AGENTS_DATA_SOURCES,
            "state": _AGENTS_STATE,
            "actions": _AGENTS_ACTIONS,
            "effects": _AGENTS_EFFECTS,
            "refresh_policy": _AGENTS_REFRESH_POLICY,
        },
    ),
)
