from unittest.mock import Mock, patch

from src.api.internal import user_management
from src.lib.user_management.models import GroupRole


@patch("src.api.internal.user_management.get_user_manager")
def test_internal_create_user_delegates_to_user_manager(mock_get_user_manager):
    manager = Mock()
    manager.create_user.return_value = {"id": 1, "username": "nick"}
    mock_get_user_manager.return_value = manager

    result = user_management.create_user("nick", "pw")

    assert result == {"id": 1, "username": "nick"}
    manager.create_user.assert_called_once_with(username="nick", password="pw")


@patch("src.api.internal.user_management.get_user_manager")
def test_internal_user_crud_methods_delegate(mock_get_user_manager):
    manager = Mock()
    manager.verify_user.return_value = True
    manager.edit_user.return_value = {"id": 1, "username": "nick-updated"}
    manager.delete_user.return_value = True
    manager.list_users.return_value = [{"id": 1, "username": "nick-updated"}]
    mock_get_user_manager.return_value = manager

    assert user_management.verify_user("nick", "pw") is True
    assert user_management.edit_user(1, username="nick-updated") == {"id": 1, "username": "nick-updated"}
    assert user_management.delete_user(1) is True
    assert user_management.list_users() == [{"id": 1, "username": "nick-updated"}]

    manager.verify_user.assert_called_once_with(username="nick", password="pw")
    manager.edit_user.assert_called_once_with(
        user_id=1,
        username="nick-updated",
        password=None,
        is_enabled=None,
    )
    manager.delete_user.assert_called_once_with(user_id=1)
    manager.list_users.assert_called_once_with()


@patch("src.api.internal.user_management.get_group_manager")
def test_internal_group_methods_delegate(mock_get_group_manager):
    manager = Mock()
    manager.create_group.return_value = {"id": 10, "name": "team"}
    manager.delete_group.return_value = True
    manager.list_groups.return_value = [{"id": 10, "name": "team"}]
    manager.list_group_members.return_value = [{"id": 100, "group_id": 10, "user_id": 1}]
    manager.list_user_groups.return_value = [{"id": 100, "group_id": 10, "user_id": 1}]
    manager.add_member.return_value = {"id": 100, "group_id": 10, "user_id": 1}
    mock_get_group_manager.return_value = manager

    assert user_management.create_group("team", 1, "core team") == {"id": 10, "name": "team"}
    assert user_management.delete_group(10) is True
    assert user_management.list_groups() == [{"id": 10, "name": "team"}]
    assert user_management.list_group_members(10) == [{"id": 100, "group_id": 10, "user_id": 1}]
    assert user_management.list_user_groups(1) == [{"id": 100, "group_id": 10, "user_id": 1}]
    assert user_management.add_member(10, 1, GroupRole.OWNER) == {"id": 100, "group_id": 10, "user_id": 1}

    manager.create_group.assert_called_once_with(
        name="team",
        created_by_user_id=1,
        description="core team",
    )
    manager.delete_group.assert_called_once_with(group_id=10)
    manager.list_groups.assert_called_once_with()
    manager.list_group_members.assert_called_once_with(group_id=10)
    manager.list_user_groups.assert_called_once_with(user_id=1)
    manager.add_member.assert_called_once_with(group_id=10, user_id=1, role=GroupRole.OWNER)
