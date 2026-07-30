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


# User/Group/Membership form fields
_USER_FORM_FIELDS = (
    ViewComponent(
        component_id="user-item-kind-field",
        component_type="field",
        properties={"label": "Type", "field_type": "select", "options": ("user", "group", "membership"), "default": "user"},
    ),
    ViewComponent(
        component_id="user-username-field",
        component_type="field",
        properties={"label": "Username", "field_type": "text"},
    ),
    ViewComponent(
        component_id="user-password-field",
        component_type="field",
        properties={"label": "Password", "field_type": "password"},
    ),
    ViewComponent(
        component_id="user-name-field",
        component_type="field",
        properties={"label": "Group name", "field_type": "text"},
    ),
    ViewComponent(
        component_id="user-description-field",
        component_type="field",
        properties={"label": "Group description", "field_type": "textarea"},
    ),
    ViewComponent(
        component_id="user-workspace-root-field",
        component_type="field",
        properties={"label": "Group workspace root", "field_type": "text"},
    ),
    ViewComponent(
        component_id="user-group-id-field",
        component_type="field",
        properties={"label": "Group ID", "field_type": "number"},
    ),
    ViewComponent(
        component_id="user-member-kind-field",
        component_type="field",
        properties={"label": "Member kind", "field_type": "select", "options": ("user", "agent"), "default": "user"},
    ),
    ViewComponent(
        component_id="user-user-id-field",
        component_type="field",
        properties={"label": "User ID", "field_type": "number"},
    ),
    ViewComponent(
        component_id="user-agent-id-field",
        component_type="field",
        properties={"label": "Agent", "field_type": "select", "binding_source": "agents", "binding_path": "items"},
    ),
    ViewComponent(
        component_id="user-role-field",
        component_type="field",
        properties={"label": "Role", "field_type": "select", "options": ("owner", "admin", "member"), "default": "member"},
    ),
    ViewComponent(
        component_id="user-is-enabled-field",
        component_type="field",
        properties={"label": "Enabled", "field_type": "checkbox", "default": True},
    ),
)

# Users view presentation tree
_USERS_PRESENTATION = ViewComponent(
    component_id="users-page",
    component_type="page",
    properties={"title": "Users & Groups", "caption": "Create users, edit your account, and manage the groups you own."},
    children=(
        ViewComponent(
            component_id="users-collection",
            component_type="collection",
            binding=ViewBinding(source="users", path="items"),
            children=(
                ViewComponent(
                    component_id="users-table",
                    component_type="table",
                    properties={
                        "columns": [
                            {"key": "item_kind", "label": "Type"},
                            {"key": "username", "label": "Username"},
                            {"key": "name", "label": "Group"},
                            {"key": "group_id", "label": "Group ID"},
                            {"key": "member_kind", "label": "Member Kind"},
                            {"key": "role", "label": "Role"},
                            {"key": "is_enabled", "label": "Enabled"},
                        ],
                    },
                    action_keys=("edit", "delete"),
                ),
            ),
        ),
        ViewComponent(
            component_id="users-view-actions",
            component_type="actions",
            properties={"label": "Create"},
            action_keys=("create",),
        ),
        ViewComponent(
            component_id="create-user-form",
            component_type="form",
            properties={"title": "Create user, group, or membership", "submit_label": "Create"},
            children=_USER_FORM_FIELDS,
            action_keys=("create",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_create_form")),
        ),
        ViewComponent(
            component_id="edit-user-form",
            component_type="form",
            properties={"title": "Edit user, group, or membership", "submit_label": "Save"},
            children=_USER_FORM_FIELDS,
            action_keys=("edit",),
            visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_edit_form")),
        ),
    ),
)

# Users view data sources
_USERS_DATA_SOURCES = (
    ViewDataSource(
        key="users",
        kind="collection",
        operation="users:list",
        parameters={"label_keys": ["username", "name"], "value_key": "id", "default_label": "Unnamed", "include_empty": True},
    ),
    ViewDataSource(
        key="agents",
        kind="collection",
        operation="agents:list",
        parameters={"label_keys": ["name"], "value_key": "id", "default_label": "Unnamed agent", "include_empty": True},
    ),
)

# Users view state
_USERS_STATE = (
    ViewStateDefinition(key="selected_user_id", value_type="string", default=""),
    ViewStateDefinition(key="show_create_form", value_type="boolean", default=False),
    ViewStateDefinition(key="show_edit_form", value_type="boolean", default=False),
    ViewStateDefinition(key="edit_target_id", value_type="string", default=""),
)

# Users view actions
_USERS_ACTIONS = (
    ViewAction(
        key="create",
        intent="create",
        label="Create",
        scope="view",
        style="primary",
        operation="users:create",
        payload={"command_id": "users.create"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_create_form", value=False),
            ViewEffect(effect_type="refresh_view", target="users.users.view"),
            ViewEffect(effect_type="show_notification", value="Entity created successfully"),
        ),
    ),
    ViewAction(
        key="edit",
        intent="edit",
        label="Edit",
        scope="item",
        operation="users:edit",
        payload={"command_id": "users.edit"},
        success_effects=(
            ViewEffect(effect_type="set_state", target="show_edit_form", value=False),
            ViewEffect(effect_type="set_state", target="selected_user_id", value="$item.id"),
            ViewEffect(effect_type="refresh_view", target="users.users.view"),
        ),
    ),
    ViewAction(
        key="delete",
        intent="delete",
        label="Delete / Disable",
        scope="item",
        style="danger",
        operation="users:delete",
        payload={"command_id": "users.delete"},
        confirmation=True,
        success_effects=(
            ViewEffect(effect_type="set_state", target="selected_user_id", value=""),
            ViewEffect(effect_type="refresh_view", target="users.users.view"),
            ViewEffect(effect_type="show_notification", value="Entity deleted/disabled"),
        ),
    ),
)

# Users view effects
_USERS_EFFECTS = ()

# Users view refresh policy
_USERS_REFRESH_POLICY = ViewRefreshPolicy(mode="on_intent")


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="users",
        action_id="users.users",
        view_id="users.users.view",
        name="Users",
        description="Create users, edit your account, and manage the groups you own.",
        metadata={
            "view_contract_ready": True,
            "object_type": "users",
            "singular_label": "User",
            "plural_label": "Users & Groups",
            "empty_state": "No users or groups are available yet.",
            "presentation": _USERS_PRESENTATION,
            "data_sources": _USERS_DATA_SOURCES,
            "state": _USERS_STATE,
            "actions": _USERS_ACTIONS,
            "effects": _USERS_EFFECTS,
            "refresh_policy": _USERS_REFRESH_POLICY,
        },
    ),
)
