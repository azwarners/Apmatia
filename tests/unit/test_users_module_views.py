from __future__ import annotations

import pytest

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import Registry
from apmatia.modules.users.commands import COMMAND_DESCRIPTORS
from apmatia.modules.users.manager import GroupManager, UserManager
from apmatia.modules.users.module import APMATIA_USERS_MODULE, register
from apmatia.modules.users.module_views import UsersModuleViewProvider
from apmatia.modules.users.sqlite_repositories import SQLiteUserManagementBundle
from apmatia.modules.users.views import VIEW_DESCRIPTORS


def _provider(tmp_path):
    bundle = SQLiteUserManagementBundle(tmp_path / "users.db")
    users = UserManager(bundle.users)
    groups = GroupManager(bundle.groups, bundle.memberships)
    return UsersModuleViewProvider(
        user_manager_factory=lambda: users,
        group_manager_factory=lambda: groups,
    ), users, groups


def _command(verb: str):
    return next(command for command in COMMAND_DESCRIPTORS if command.metadata["verb"] == verb)


def test_users_module_is_stable_infrastructure_with_users_view():
    registry = Registry()
    register(registry)

    assert APMATIA_USERS_MODULE.status == "stable"
    assert APMATIA_USERS_MODULE.category == "infrastructure"
    assert [module.module_id for module in registry.list_modules()] == ["users"]
    assert [view.view_id for view in registry.list_views()] == ["users.groups.view", "users.users.view"]


def test_users_view_lists_safe_users_groups_and_owned_memberships(tmp_path):
    provider, users, groups = _provider(tmp_path)
    owner = users.create_user("owner", "secret")
    member = users.create_user("member", "secret")
    group = groups.create_group("team", owner.id or 0)
    groups.add_member(group.id or 0, member.id or 0)

    items = provider.list_items(
        view=VIEW_DESCRIPTORS[0],
        context=ModuleViewContext(user_id=owner.id, group_ids=frozenset({group.id or 0})),
    )

    assert {item["item_kind"] for item in items} == {"user"}
    assert all("password_hash" not in item for item in items)

    groups_view = next(view for view in VIEW_DESCRIPTORS if view.view_id == "users.groups.view")
    group_items = provider.list_items(
        view=groups_view,
        context=ModuleViewContext(user_id=owner.id, group_ids=frozenset({group.id or 0})),
    )
    assert {item["item_kind"] for item in group_items} == {"group"}


def test_users_view_commands_enforce_account_and_group_ownership(tmp_path):
    provider, users, groups = _provider(tmp_path)
    owner = users.create_user("owner", "secret")
    outsider = users.create_user("outsider", "secret")
    group = groups.create_group("team", owner.id or 0)

    with pytest.raises(ValueError, match="User access denied"):
        provider.execute_command(
            command=_command("edit_user"),
            payload={"item_id": owner.id, "username": "stolen"},
            context=ModuleViewContext(user_id=outsider.id),
        )

    with pytest.raises(ValueError, match="Group owner access required"):
        provider.execute_command(
            command=_command("edit_group"),
            payload={"item_id": group.id, "name": "stolen"},
            context=ModuleViewContext(user_id=outsider.id),
        )

    result = provider.execute_command(
        command=_command("edit_group"),
        payload={"item_id": group.id, "name": "renamed"},
        context=ModuleViewContext(user_id=owner.id),
    )
    assert result["item"]["name"] == "renamed"
