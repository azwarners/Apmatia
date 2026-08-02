from __future__ import annotations

from apmatia.core.registry import ViewContribution
from apmatia.core.view_contract.models import (
    ViewAction,
    ViewBinding,
    ViewComponent,
    ViewCondition,
    ViewDataSource,
    ViewEffect,
    ViewRefreshPolicy,
    ViewStateDefinition,
)


_USER_FORM_FIELDS = (
    ViewComponent(component_id="user-username-field", component_type="field", properties={"label": "Username", "field_type": "text"}),
    ViewComponent(component_id="user-password-field", component_type="field", properties={"label": "Password", "field_type": "password"}),
    ViewComponent(component_id="user-is-enabled-field", component_type="field", properties={"label": "Enabled", "field_type": "checkbox", "default": True}),
)

_GROUP_FORM_FIELDS = (
    ViewComponent(component_id="group-name-field", component_type="field", properties={"label": "Group name", "field_type": "text"}),
    ViewComponent(component_id="group-description-field", component_type="field", properties={"label": "Description", "field_type": "textarea"}),
    ViewComponent(component_id="group-workspace-root-field", component_type="field", properties={"label": "Workspace root", "field_type": "text"}),
)

_USERS_DATA_SOURCES = (
    ViewDataSource(key="users", kind="collection", operation="users:list", parameters={"value_key": "id"}),
)

_USERS_STATE = (
    ViewStateDefinition(key="show_create_form", value_type="boolean", default=False),
    ViewStateDefinition(key="show_edit_form", value_type="boolean", default=False),
)

_USER_ACTIONS = (
    ViewAction(key="create", intent="create", label="Create user", scope="view", style="primary", operation="users:create", payload={"command_id": "users.create", "item_kind": "user"}),
    ViewAction(key="edit", intent="edit", label="Edit", scope="item", operation="users:edit", payload={"command_id": "users.edit", "item_kind": "user"}),
    ViewAction(key="delete", intent="delete", label="Delete", scope="item", style="danger", operation="users:delete", payload={"command_id": "users.delete", "item_kind": "user"}, confirmation=True),
)

_GROUP_ACTIONS = (
    ViewAction(key="create", intent="create", label="Create group", scope="view", style="primary", operation="users:create", payload={"command_id": "users.create", "item_kind": "group"}),
    ViewAction(key="edit", intent="edit", label="Edit", scope="item", operation="users:edit", payload={"command_id": "users.edit", "item_kind": "group"}),
    ViewAction(key="delete", intent="delete", label="Delete", scope="item", style="danger", operation="users:delete", payload={"command_id": "users.delete", "item_kind": "group"}, confirmation=True),
)


def _collection(component_id: str, *, columns: list[dict[str, str]], action_keys: tuple[str, ...]) -> ViewComponent:
    return ViewComponent(
        component_id=component_id,
        component_type="collection",
        binding=ViewBinding(source="users", path="items"),
        children=(
            ViewComponent(
                component_id=f"{component_id}-table",
                component_type="table",
                properties={"columns": columns},
                binding=ViewBinding(source="users", path="items"),
                action_keys=action_keys,
            ),
        ),
    )


_USERS_PRESENTATION = ViewComponent(
    component_id="users-page",
    component_type="page",
    properties={"title": "Users", "caption": "Manage Apmatia user accounts."},
    children=(
        _collection("users-collection", columns=[
            {"key": "username", "label": "Username"},
            {"key": "is_enabled", "label": "Enabled"},
            {"key": "created_at", "label": "Created"},
        ], action_keys=("edit", "delete")),
        ViewComponent(component_id="users-view-actions", component_type="actions", properties={"label": "Create user"}, action_keys=("create",)),
        ViewComponent(component_id="create-user-form", component_type="form", properties={"title": "Create user", "submit_label": "Create"}, children=_USER_FORM_FIELDS, action_keys=("create",), visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_create_form"))),
        ViewComponent(component_id="edit-user-form", component_type="form", properties={"title": "Edit user", "submit_label": "Save"}, children=_USER_FORM_FIELDS, action_keys=("edit",), visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_edit_form"))),
    ),
)

_GROUPS_PRESENTATION = ViewComponent(
    component_id="groups-page",
    component_type="page",
    properties={"title": "Groups", "caption": "Manage groups you belong to and own."},
    children=(
        _collection("groups-collection", columns=[
            {"key": "name", "label": "Group"},
            {"key": "description", "label": "Description"},
            {"key": "created_by_user_id", "label": "Owner ID"},
        ], action_keys=("edit", "delete")),
        ViewComponent(component_id="groups-view-actions", component_type="actions", properties={"label": "Create group"}, action_keys=("create",)),
        ViewComponent(component_id="create-group-form", component_type="form", properties={"title": "Create group", "submit_label": "Create"}, children=_GROUP_FORM_FIELDS, action_keys=("create",), visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_create_form"))),
        ViewComponent(component_id="edit-group-form", component_type="form", properties={"title": "Edit group", "submit_label": "Save"}, children=_GROUP_FORM_FIELDS, action_keys=("edit",), visible_when=ViewCondition(operator="equals", operands=(True, "$state.show_edit_form"))),
    ),
)


def _effects(view_id: str) -> tuple[ViewEffect, ...]:
    return (
        ViewEffect(effect_type="refresh_view", target=view_id),
        ViewEffect(effect_type="show_notification", value="Changes saved successfully"),
    )


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="users", action_id="users.users", view_id="users.users.view", name="Users",
        description="Manage Apmatia user accounts.",
        metadata={"view_contract_ready": True, "object_type": "users", "singular_label": "User", "plural_label": "Users", "empty_state": "No users have been created yet.", "presentation": _USERS_PRESENTATION, "data_sources": _USERS_DATA_SOURCES, "state": _USERS_STATE, "actions": _USER_ACTIONS, "effects": _effects("users.users.view"), "refresh_policy": ViewRefreshPolicy(mode="on_intent")},
    ),
    ViewContribution(
        module_id="users", action_id="users.groups", view_id="users.groups.view", name="Groups",
        description="Manage groups you belong to and own.",
        metadata={"view_contract_ready": True, "object_type": "groups", "singular_label": "Group", "plural_label": "Groups", "empty_state": "No groups are available yet.", "presentation": _GROUPS_PRESENTATION, "data_sources": _USERS_DATA_SOURCES, "state": _USERS_STATE, "actions": _GROUP_ACTIONS, "effects": _effects("users.groups.view"), "refresh_policy": ViewRefreshPolicy(mode="on_intent")},
    ),
)
