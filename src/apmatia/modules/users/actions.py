from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="users",
        action_id="users.users",
        name="Users",
        description="Authenticate accounts and manage users, groups, and memberships.",
        metadata={"object_type": "users"},
    ),
)
