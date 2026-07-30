from __future__ import annotations

from apmatia.core.registry import CommandContribution


_VERBS = (
    "list",
    "create",
    "edit",
    "delete",
    "create_user",
    "edit_user",
    "delete_user",
    "create_group",
    "edit_group",
    "delete_group",
    "add_member",
    "set_membership_enabled",
)


_INPUT_FIELDS: dict[str, list[dict[str, object]]] = {
    "create_user": [
        {"key": "username", "required": True},
        {"key": "password", "field_type": "password", "required": True},
    ],
    "edit_user": [
        {"key": "item_id", "label": "User ID", "data_type": "number", "required": True},
        {"key": "username"},
        {"key": "password", "field_type": "password"},
        {"key": "is_enabled", "data_type": "boolean"},
    ],
    "delete_user": [{"key": "item_id", "label": "User ID", "data_type": "number", "required": True}],
    "create_group": [
        {"key": "name", "required": True},
        {"key": "description"},
        {"key": "workspace_root"},
    ],
    "edit_group": [
        {"key": "group_id", "data_type": "number", "required": True},
        {"key": "name"},
        {"key": "description"},
        {"key": "workspace_root"},
    ],
    "delete_group": [{"key": "group_id", "data_type": "number", "required": True}],
    "add_member": [
        {"key": "group_id", "data_type": "number", "required": True},
        {"key": "member_kind", "options": ["user", "agent"], "required": True},
        {"key": "user_id", "data_type": "number"},
        {"key": "agent_id", "data_type": "number"},
        {"key": "role", "options": ["owner", "admin", "member"], "required": True},
    ],
    "set_membership_enabled": [
        {"key": "group_id", "data_type": "number", "required": True},
        {"key": "membership_id", "data_type": "number", "required": True},
        {"key": "enabled", "data_type": "boolean"},
    ],
}

COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = tuple(
    CommandContribution(
        module_id="users",
        command_id=f"users.{verb}",
        path=("users", verb),
        name=f"Users {verb.replace('_', ' ').title()}",
        description=f"{verb.replace('_', ' ').title()} through the users infrastructure module.",
        metadata={
            "object_type": "users",
            "verb": verb,
            "collection_view_id": "users.users.view",
            "input_fields": _INPUT_FIELDS.get(verb, []),
        },
    )
    for verb in _VERBS
)
