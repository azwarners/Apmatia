from __future__ import annotations

from src.core.group_access import (
    enabled_group_ids as _enabled_group_ids,
    is_group_member as _is_group_member,
    is_group_owner as _is_group_owner,
    visible_groups as _visible_groups,
)


def enabled_group_ids(memberships: list[dict | object]) -> set[int]:
    return _enabled_group_ids(memberships)


def is_group_member(memberships: list[dict | object], group_id: int) -> bool:
    return _is_group_member(memberships, group_id)


def is_group_owner(memberships: list[dict | object], user_id: int) -> bool:
    return _is_group_owner(memberships, user_id)


def visible_groups(groups: list[dict | object], member_group_ids: set[int]) -> list[dict | object]:
    return _visible_groups(groups, member_group_ids)
