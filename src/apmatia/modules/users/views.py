from __future__ import annotations

from apmatia.core.registry import ViewContribution


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="users",
        action_id="users.users",
        view_id="users.users.view",
        name="Users",
        description="Create users, edit your account, and manage the groups you own.",
        metadata={
            "object_type": "users",
            "singular_label": "User",
            "plural_label": "Users & Groups",
            "empty_state": "No users or groups are available yet.",
            "commands": {verb: f"users.{verb}" for verb in (
                "list",
                "create_user",
                "edit_user",
                "delete_user",
                "create_group",
                "edit_group",
                "delete_group",
                "add_member",
                "set_membership_enabled",
            )},
            "schema": {
                "version": 1,
                "resources": {
                    "users": {"item_kind": "user", "key": "id"},
                    "groups": {"item_kind": "group", "key": "id"},
                    "memberships": {"item_kind": "membership", "key": "id"},
                },
            },
            "ui": {"render_mode": "collection", "renderer": "users"},
        },
    ),
)
