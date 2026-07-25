from __future__ import annotations

from apmatia.core.registry import CommandContribution


_VERBS = (
    "list",
    "create_user",
    "edit_user",
    "delete_user",
    "create_group",
    "edit_group",
    "delete_group",
    "add_member",
    "set_membership_enabled",
)

COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = tuple(
    CommandContribution(
        module_id="users",
        action_id="users.users",
        command_id=f"users.users.{verb}",
        path=("users", verb),
        name=f"Users {verb.replace('_', ' ').title()}",
        description=f"{verb.replace('_', ' ').title()} through the users infrastructure module.",
        metadata={
            "object_type": "users",
            "verb": verb,
            "collection_view_id": "users.users.view",
        },
    )
    for verb in _VERBS
)
