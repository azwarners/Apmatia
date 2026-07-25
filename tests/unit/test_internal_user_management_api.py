from unittest.mock import Mock, patch

from apmatia.api.internal import users
from apmatia.modules.users.models import GroupMemberKind, GroupRole


@patch("apmatia.api.internal.users.get_user_manager")
def test_internal_create_user_delegates_to_user_manager(mock_get_user_manager):
    manager = Mock()
    manager.create_user.return_value = {"id": 1, "username": "nick"}
    mock_get_user_manager.return_value = manager

    result = users.create_user("nick", "pw")

    assert result == {"id": 1, "username": "nick"}
    manager.create_user.assert_called_once_with(username="nick", password="pw")


@patch("apmatia.api.internal.users.get_user_manager")
def test_internal_user_crud_methods_delegate(mock_get_user_manager):
    manager = Mock()
    manager.verify_user.return_value = True
    manager.edit_user.return_value = {"id": 1, "username": "nick-updated"}
    manager.delete_user.return_value = True
    manager.list_users.return_value = [{"id": 1, "username": "nick-updated"}]
    mock_get_user_manager.return_value = manager

    assert users.verify_user("nick", "pw") is True
    assert users.edit_user(1, username="nick-updated") == {"id": 1, "username": "nick-updated"}
    assert users.delete_user(1) is True
    assert users.list_users() == [{"id": 1, "username": "nick-updated"}]

    manager.verify_user.assert_called_once_with(username="nick", password="pw")
    manager.edit_user.assert_called_once_with(
        user_id=1,
        username="nick-updated",
        password=None,
        is_enabled=None,
    )
    manager.delete_user.assert_called_once_with(user_id=1)
    manager.list_users.assert_called_once_with()


@patch("apmatia.api.internal.users.get_group_manager")
def test_internal_group_methods_delegate(mock_get_group_manager):
    manager = Mock()
    manager.create_group.return_value = {"id": 10, "name": "team"}
    manager.edit_group.return_value = {"id": 10, "name": "team-renamed"}
    manager.delete_group.return_value = True
    manager.list_groups.return_value = [{"id": 10, "name": "team"}]
    manager.list_group_members.return_value = [{"id": 100, "group_id": 10, "user_id": 1, "member_kind": "user"}]
    manager.list_user_groups.return_value = [{"id": 100, "group_id": 10, "user_id": 1, "member_kind": "user"}]
    manager.add_member.return_value = {"id": 100, "group_id": 10, "user_id": 1, "member_kind": "user"}
    manager.set_membership_enabled.return_value = {"id": 100, "group_id": 10, "user_id": 1, "member_kind": "user"}
    mock_get_group_manager.return_value = manager

    assert users.create_group("team", 1, "core team") == {"id": 10, "name": "team"}
    assert users.edit_group(10, name="team-renamed") == {"id": 10, "name": "team-renamed"}
    assert users.delete_group(10) is True
    assert users.list_groups() == [{"id": 10, "name": "team"}]
    assert users.list_group_members(10) == [{"id": 100, "group_id": 10, "user_id": 1, "member_kind": "user"}]
    assert users.list_user_groups(1) == [{"id": 100, "group_id": 10, "user_id": 1, "member_kind": "user"}]
    assert users.add_member(10, 1, GroupRole.OWNER) == {"id": 100, "group_id": 10, "user_id": 1, "member_kind": "user"}
    assert users.set_membership_enabled(100, False) == {"id": 100, "group_id": 10, "user_id": 1, "member_kind": "user"}

    manager.create_group.assert_called_once_with(
        name="team",
        created_by_user_id=1,
        description="core team",
        workspace_root="",
    )
    manager.edit_group.assert_called_once_with(
        group_id=10,
        name="team-renamed",
        description=None,
        workspace_root=None,
    )
    manager.delete_group.assert_called_once_with(group_id=10)
    manager.list_groups.assert_called_once_with()
    manager.list_group_members.assert_called_once_with(group_id=10)
    manager.list_user_groups.assert_called_once_with(user_id=1)
    manager.add_member.assert_called_once_with(
        group_id=10,
        user_id=1,
        role=GroupRole.OWNER,
        agent_id=None,
        member_kind=GroupMemberKind.USER,
    )
    manager.set_membership_enabled.assert_called_once_with(membership_id=100, enabled=False)


@patch("apmatia.api.internal.users.get_group_manager")
def test_internal_group_methods_support_agent_members(mock_get_group_manager):
    manager = Mock()
    manager.add_member.return_value = {"id": 101, "group_id": 10, "agent_id": 77, "member_kind": "agent"}
    mock_get_group_manager.return_value = manager

    result = users.add_member(10, agent_id=77, member_kind=GroupMemberKind.AGENT)

    assert result == {"id": 101, "group_id": 10, "agent_id": 77, "member_kind": "agent"}
    manager.add_member.assert_called_once_with(
        group_id=10,
        user_id=None,
        role=GroupRole.MEMBER,
        agent_id=77,
        member_kind=GroupMemberKind.AGENT,
    )
