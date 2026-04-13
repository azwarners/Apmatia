from types import SimpleNamespace

from src.core.group_access import enabled_group_ids, is_group_member, is_group_owner, visible_groups
from src.lib.user_management.models import GroupRole


def test_enabled_group_ids_and_group_member_support_dicts_and_objects():
    memberships = [
        {"group_id": "1", "is_enabled": True},
        {"group_id": 3, "is_enabled": False},
        SimpleNamespace(group_id=2, is_enabled=True),
    ]

    assert enabled_group_ids(memberships) == {1, 2}
    assert is_group_member(memberships, 2) is True
    assert is_group_member(memberships, 3) is False


def test_is_group_owner_requires_owner_role_and_enabled_membership():
    memberships = [
        {"user_id": 10, "role": GroupRole.OWNER.value, "is_enabled": True},
        {"user_id": 11, "role": GroupRole.OWNER.value, "is_enabled": False},
        SimpleNamespace(
            user_id=12,
            role=SimpleNamespace(value=GroupRole.OWNER.value),
            is_enabled=True,
        ),
        {"user_id": 13, "role": GroupRole.MEMBER.value, "is_enabled": True},
    ]

    assert is_group_owner(memberships, 10) is True
    assert is_group_owner(memberships, 12) is True
    assert is_group_owner(memberships, 11) is False
    assert is_group_owner(memberships, 13) is False


def test_visible_groups_filters_by_membership_ids_for_dicts_and_objects():
    groups = [
        {"id": 1, "name": "one"},
        SimpleNamespace(id=2, name="two"),
        {"id": 3, "name": "three"},
    ]

    visible = visible_groups(groups, member_group_ids={2, 3})

    assert visible == [groups[1], groups[2]]
