from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apmatia.api.internal.group_access import enabled_group_ids
from apmatia.api.internal.user_management import list_user_groups
from apmatia.core.module_view_runtime import execute_module_command, list_module_view_items


def get_module_view_items(view_id: str, *, user_id: int) -> list[dict[str, Any]]:
    return list_module_view_items(
        view_id,
        user_id=user_id,
        group_ids=enabled_group_ids(list_user_groups(user_id)),
    )


def run_module_command(
    command_id: str,
    *,
    payload: Mapping[str, Any] | None = None,
    user_id: int,
) -> dict[str, Any] | None:
    return execute_module_command(
        command_id,
        payload=payload,
        user_id=user_id,
        group_ids=enabled_group_ids(list_user_groups(user_id)),
    )
