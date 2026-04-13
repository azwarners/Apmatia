from __future__ import annotations

from src.core.discussions import discussion_state


def snapshot(*, user_id: int, member_group_ids: set[int]):
    return discussion_state.snapshot(user_id=user_id, member_group_ids=member_group_ids)


def start_prompt(*, user_id: int, prompt: str, member_group_ids: set[int]) -> str:
    return discussion_state.start_prompt(user_id=user_id, prompt=prompt, member_group_ids=member_group_ids)


def reset_discussion(*, user_id: int) -> str:
    return discussion_state.reset_discussion(user_id=user_id)


def set_system_prompt(*, user_id: int, system_prompt: str, member_group_ids: set[int]) -> None:
    discussion_state.set_system_prompt(user_id=user_id, system_prompt=system_prompt, member_group_ids=member_group_ids)


def list_tree(*, user_id: int, member_group_ids: set[int]) -> dict:
    return discussion_state.list_tree(user_id=user_id, member_group_ids=member_group_ids)


def create_folder(*, owner_user_id: int, name: str, parent_id: int | None = None) -> dict:
    return discussion_state.create_folder(owner_user_id=owner_user_id, name=name, parent_id=parent_id)


def update_folder(*, owner_user_id: int, folder_id: int, **updates) -> dict:
    return discussion_state.update_folder(owner_user_id=owner_user_id, folder_id=folder_id, **updates)


def delete_folder(*, owner_user_id: int, folder_id: int, force: bool = False) -> dict:
    return discussion_state.delete_folder(owner_user_id=owner_user_id, folder_id=folder_id, force=force)


def restore_folder(*, owner_user_id: int, folder_id: int) -> dict:
    return discussion_state.restore_folder(owner_user_id=owner_user_id, folder_id=folder_id)


def restore_discussion(*, owner_user_id: int, discussion_id: str) -> dict:
    return discussion_state.restore_discussion(owner_user_id=owner_user_id, discussion_id=discussion_id)


def list_trash(*, owner_user_id: int) -> dict:
    return discussion_state.list_trash(owner_user_id=owner_user_id)


def create_discussion(*, owner_user_id: int, title: str, group_id: int | None = None, folder_id: int | None = None) -> dict:
    return discussion_state.create_discussion(owner_user_id=owner_user_id, title=title, group_id=group_id, folder_id=folder_id)


def update_discussion(*, owner_user_id: int, discussion_id: str, **updates) -> dict:
    return discussion_state.update_discussion(owner_user_id=owner_user_id, discussion_id=discussion_id, **updates)


def open_discussion(*, user_id: int, discussion_id: str, member_group_ids: set[int]) -> None:
    discussion_state.open_discussion(user_id=user_id, discussion_id=discussion_id, member_group_ids=member_group_ids)
