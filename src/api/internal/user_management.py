from __future__ import annotations

from src.core.user_management.models import GroupRole, UserId
from src.core.user_management.runtime import get_group_manager, get_user_manager


def create_user(username: str, password: str):
    return get_user_manager().create_user(username=username, password=password)


def verify_user(username: str, password: str) -> bool:
    return get_user_manager().verify_user(username=username, password=password)


def edit_user(
    user_id: UserId,
    username: str | None = None,
    password: str | None = None,
    is_enabled: bool | None = None,
):
    return get_user_manager().edit_user(
        user_id=user_id,
        username=username,
        password=password,
        is_enabled=is_enabled,
    )


def delete_user(user_id: UserId) -> bool:
    return get_user_manager().delete_user(user_id=user_id)


def list_users():
    return get_user_manager().list_users()


def create_group(name: str, created_by_user_id: UserId, description: str = ""):
    return get_group_manager().create_group(
        name=name,
        created_by_user_id=created_by_user_id,
        description=description,
    )


def delete_group(group_id: int) -> bool:
    return get_group_manager().delete_group(group_id=group_id)


def list_groups():
    return get_group_manager().list_groups()


def add_member(group_id: int, user_id: UserId, role: GroupRole = GroupRole.MEMBER):
    return get_group_manager().add_member(group_id=group_id, user_id=user_id, role=role)


def list_group_members(group_id: int):
    return get_group_manager().list_group_members(group_id=group_id)


def list_user_groups(user_id: UserId):
    return get_group_manager().list_user_groups(user_id=user_id)
