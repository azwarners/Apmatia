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

from .models import MemoryItem

# Memory form fields
_MEMORY_FORM_FIELDS = (
    ViewComponent(
        component_id="memory-title-field",
        component_type="field",
        properties={"label": "Title", "field_type": "text", "required": True, "placeholder": "Short memory title"},
    ),
    ViewComponent(
        component_id="memory-content-field",
        component_type="field",
        properties={"label": "Content", "field_type": "textarea", "required": True, "placeholder": "Memory content"},
    ),
    ViewComponent(
        component_id="memory-tags-field",
        component_type="field",
        properties={"label": "Tags", "field_type": "text", "placeholder": "comma, separated, tags"},
    ),
    ViewComponent(
        component_id="memory-owner-agent-id-field",
        component_type="field",
        properties={"label": "Agent ID", "field_type": "text", "help_text": "Leave blank for a user-owned memory."},
    ),
    ViewComponent(
        component_id="memory-visibility-field",
        component_type="field",
        properties={"label": "Visibility", "field_type": "select", "options": ("draft", "user_visible", "private")},
    ),
    ViewComponent(
        component_id="memory-status-field",
        component_type="field",
        properties={"label": "Status", "field_type": "select", "options": ("active", "archived", "deleted")},
    ),
    ViewComponent(
        component_id="memory-source-discussion-id-field",
        component_type="field",
        properties={"label": "Source Discussion ID", "field_type": "text"},
    ),
    ViewComponent(
        component_id="memory-source-message-ids-field",
        component_type="field",
        properties={"label": "Source Message IDs", "field_type": "text", "placeholder": "comma, separated, message IDs"},
    ),
)

# Memories view presentation tree
_MEMORIES_PRESENTATION = ViewComponent(
    component_id="memories-page",
    component_type="page",
    properties={"title": "Memories", "caption": "Browse and manage memories visible to your user and groups."},
    children=(
        ViewComponent(
            component_id="memories-collection",
            component_type="collection",
            binding=ViewBinding(source="memories", path="items"),
            children=(
                ViewComponent(
                    component_id="memories-table",
                    component_type="table",
                    properties={
                        "columns": [
                            {"key": "title", "label": "Title"},
                            {"key": "owner_agent_id", "label": "Agent ID"},
                            {"key": "visibility", "label": "Visibility"},
                            {"key": "status", "label": "Status"},
                            {"key": "tags", "label": "Tags"},
                        ],
                    },
                    action_keys=("edit", "delete"),
                ),
            ),
        ),
        ViewComponent(
            component_id="memories-view-actions",
            component_type="actions",
            properties={"label": "Create memory"},
            action_keys=("create",),
        ),
        ViewComponent(
            component_id="create-memory-form",
            component_type="form",
            properties={"title": "Create memory", "submit_label": "Create memory"},
            children=_MEMORY_FORM_FIELDS,
            action_keys=("create",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_create_form")),
        ),
        ViewComponent(
            component_id="edit-memory-form",
            component_type="form",
            properties={"title": "Edit memory", "submit_label": "Save memory"},
            children=_MEMORY_FORM_FIELDS,
            action_keys=("edit",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_edit_form")),
        ),
    ),
)

# Memories view data sources
_MEMORIES_DATA_SOURCES = (
    ViewDataSource(
        key="memories",
        kind="collection",
        operation="memory_manager:list",
        parameters={"label_keys": ["title"], "value_key": "id", "default_label": "Unnamed memory", "include_empty": True},
    ),
)

# Memories view state
_MEMORIES_STATE = (
    ViewStateDefinition(key="selected_memory_id", value_type="string", default=""),
    ViewStateDefinition(key="show_create_form", value_type="boolean", default=False),
    ViewStateDefinition(key="show_edit_form", value_type="boolean", default=False),
    ViewStateDefinition(key="edit_target_id", value_type="string", default=""),
)

# Memories view actions
_MEMORIES_ACTIONS = (
    ViewAction(
        key="create",
        intent="create",
        label="Create memory",
        scope="view",
        style="primary",
        operation="memory_manager:create",
        payload={"command_id": "memory_manager.create"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_create_form", value=False),
            ViewEffect(effect_type="refresh_view", target="memory_manager.memory.view"),
            ViewEffect(effect_type="show_notification", value="Memory created successfully"),
        ),
    ),
    ViewAction(
        key="edit",
        intent="edit",
        label="Edit",
        scope="item",
        operation="memory_manager:edit",
        payload={"command_id": "memory_manager.edit"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_edit_form", value=False),
            ViewEffect(effect_type="set_state", target="selected_memory_id", value="$item.id"),
            ViewEffect(effect_type="refresh_view", target="memory_manager.memory.view"),
        ),
    ),
    ViewAction(
        key="delete",
        intent="delete",
        label="Delete",
        scope="item",
        style="danger",
        operation="memory_manager:delete",
        payload={"command_id": "memory_manager.delete"},
        confirmation=True,
        success_effects=(
            ViewEffect(effect_type="set_state", target="selected_memory_id", value=""),
            ViewEffect(effect_type="refresh_view", target="memory_manager.memory.view"),
            ViewEffect(effect_type="show_notification", value="Memory deleted"),
        ),
    ),
)

# Memories view effects
_MEMORIES_EFFECTS = ()

# Memories view refresh policy
_MEMORIES_REFRESH_POLICY = ViewRefreshPolicy(mode="on_intent")


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="memory_manager",
        action_id="memory_manager.memory",
        view_id="memory_manager.memory.view",
        name="Memories",
        description="Browse and manage memories visible to your user and groups.",
        metadata={
            "view_contract_ready": True,
            "object_type": "memory",
            "singular_label": "Memory",
            "plural_label": "Memories",
            "empty_state": "No memories found.",
            "presentation": _MEMORIES_PRESENTATION,
            "data_sources": _MEMORIES_DATA_SOURCES,
            "state": _MEMORIES_STATE,
            "actions": _MEMORIES_ACTIONS,
            "effects": _MEMORIES_EFFECTS,
            "refresh_policy": _MEMORIES_REFRESH_POLICY,
        },
    ),
)
