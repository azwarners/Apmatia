from __future__ import annotations

from src.lib.user_management.models import GroupRole


def enabled_group_ids(memberships: list[dict | object]) -> set[int]:
    ids: set[int] = set()
    for membership in memberships:
        group_id = membership["group_id"] if isinstance(membership, dict) else membership.group_id
        is_enabled = membership.get("is_enabled", True) if isinstance(membership, dict) else membership.is_enabled
        if bool(is_enabled):
            ids.add(int(group_id))
    return ids


def is_group_member(memberships: list[dict | object], group_id: int) -> bool:
    return int(group_id) in enabled_group_ids(memberships)


def is_group_owner(memberships: list[dict | object], user_id: int) -> bool:
    for membership in memberships:
        m_user_id = membership["user_id"] if isinstance(membership, dict) else membership.user_id
        m_role = membership["role"] if isinstance(membership, dict) else membership.role.value
        is_enabled = membership.get("is_enabled", True) if isinstance(membership, dict) else membership.is_enabled
        if int(m_user_id) == int(user_id) and str(m_role) == GroupRole.OWNER.value and bool(is_enabled):
            return True
    return False


def visible_groups(groups: list[dict | object], member_group_ids: set[int]) -> list[dict | object]:
    visible: list[dict | object] = []
    for group in groups:
        group_id = int(group["id"]) if isinstance(group, dict) else int(group.id or 0)
        if group_id in member_group_ids:
            visible.append(group)
    return visible
