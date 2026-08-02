from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution

from .manager import GroupManager, UserManager
from .models import Group, GroupMemberKind, GroupMembership, GroupRole, User


class UsersModuleViewProvider:
    """Registry-backed API surface for the Users view."""

    def __init__(
        self,
        *,
        user_manager_factory: Callable[[], UserManager],
        group_manager_factory: Callable[[], GroupManager],
    ) -> None:
        self._user_manager_factory = user_manager_factory
        self._group_manager_factory = group_manager_factory

    @property
    def users(self) -> UserManager:
        return self._user_manager_factory()

    @property
    def groups(self) -> GroupManager:
        return self._group_manager_factory()

    def list_items(self, *, view: ViewContribution, context: ModuleViewContext) -> list[dict[str, Any]]:
        users = [_serialize_user(user) for user in self.users.list_users()]
        if view.view_id == "users.users.view":
            return users
        if view.view_id == "users.groups.view":
            return [
                _serialize_group(group)
                for group in self.groups.list_groups()
                if group.id is not None and group.id in context.group_ids
            ]

        items: list[dict[str, Any]] = users
        visible_groups = [
            group
            for group in self.groups.list_groups()
            if group.id is not None and group.id in context.group_ids
        ]
        for group in visible_groups:
            items.append(_serialize_group(group))
            if group.id is not None and self._is_group_owner(group.id, context.user_id):
                items.extend(_serialize_membership(member) for member in self.groups.list_group_members(group.id))
        return items

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        user_id = _require_authenticated_user(context)
        verb = str(command.metadata.get("verb") or command.command_id.rsplit(".", 1)[-1]).strip().lower()
        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command), context=context)}
        if verb in {"create", "edit", "delete"}:
            item = payload.get("item") if isinstance(payload.get("item"), Mapping) else {}
            item_kind = str(payload.get("item_kind") or item.get("item_kind") or "user").strip().lower()
            payload = {**item, **payload}
            payload.pop("item", None)
            if item_kind == "membership":
                verb = "add_member" if verb == "create" else "set_membership_enabled"
                payload = {
                    **payload,
                    "membership_id": payload.get("membership_id", payload.get("item_id")),
                    "enabled": False if command.metadata.get("verb") == "delete" else payload.get("is_enabled", payload.get("enabled", True)),
                }
            else:
                verb = f"{verb}_{item_kind}"
                if item_kind == "group":
                    payload = {**payload, "group_id": payload.get("group_id", payload.get("item_id"))}
        if verb == "create_user":
            user = self.users.create_user(
                username=str(payload.get("username") or ""),
                password=str(payload.get("password") or ""),
            )
            return {"status": "created", "item": _serialize_user(user)}
        if verb == "edit_user":
            target_user_id = _required_int(payload.get("item_id"), label="user ID")
            if target_user_id != user_id:
                raise ValueError("User access denied.")
            user = self.users.edit_user(
                user_id=target_user_id,
                username=_optional_text(payload, "username"),
                password=_optional_text(payload, "password"),
                is_enabled=_optional_bool(payload, "is_enabled"),
            )
            return {"status": "updated", "item": _serialize_user(user)}
        if verb == "delete_user":
            target_user_id = _required_int(payload.get("item_id"), label="user ID")
            if target_user_id != user_id:
                raise ValueError("User access denied.")
            return {"status": "deleted" if self.users.delete_user(target_user_id) else "not_found"}
        if verb == "create_group":
            group = self.groups.create_group(
                name=str(payload.get("name") or ""),
                created_by_user_id=user_id,
                description=str(payload.get("description") or ""),
                workspace_root=str(payload.get("workspace_root") or ""),
            )
            return {"status": "created", "item": _serialize_group(group)}

        group_id = _required_int(payload.get("group_id", payload.get("item_id")), label="group ID")
        self._require_group_owner(group_id, user_id)
        if verb == "edit_group":
            group = self.groups.edit_group(
                group_id=group_id,
                name=_optional_text(payload, "name"),
                description=_optional_text(payload, "description"),
                workspace_root=_optional_text(payload, "workspace_root"),
            )
            return {"status": "updated", "item": _serialize_group(group)}
        if verb == "delete_group":
            return {"status": "deleted" if self.groups.delete_group(group_id) else "not_found"}
        if verb == "add_member":
            member_kind = GroupMemberKind(str(payload.get("member_kind") or GroupMemberKind.USER.value))
            membership = self.groups.add_member(
                group_id=group_id,
                user_id=_optional_int(payload.get("user_id")),
                agent_id=_optional_int(payload.get("agent_id")),
                member_kind=member_kind,
                role=GroupRole(str(payload.get("role") or GroupRole.MEMBER.value)),
            )
            return {"status": "created", "item": _serialize_membership(membership)}
        if verb == "set_membership_enabled":
            membership_id = _required_int(payload.get("membership_id"), label="membership ID")
            membership = next(
                (member for member in self.groups.list_group_members(group_id) if member.id == membership_id),
                None,
            )
            if membership is None:
                raise ValueError(f"Membership not found in group {group_id}: {membership_id}")
            if membership.role == GroupRole.OWNER:
                raise ValueError("Owner memberships cannot be disabled.")
            updated = self.groups.set_membership_enabled(membership_id, bool(payload.get("enabled", True)))
            return {"status": "updated", "item": _serialize_membership(updated)}
        raise ValueError(f"Unsupported users command verb: {verb}")

    def _is_group_owner(self, group_id: int, user_id: int | None) -> bool:
        if user_id is None:
            return False
        return any(
            member.user_id == user_id
            and member.member_kind == GroupMemberKind.USER
            and member.role == GroupRole.OWNER
            and member.is_enabled
            for member in self.groups.list_group_members(group_id)
        )

    def _require_group_owner(self, group_id: int, user_id: int) -> None:
        if not self._is_group_owner(group_id, user_id):
            raise ValueError("Group owner access required.")


def _serialize_user(user: User) -> dict[str, Any]:
    return {
        "item_kind": "user",
        "id": user.id,
        "username": user.username,
        "is_enabled": user.is_enabled,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def _serialize_group(group: Group) -> dict[str, Any]:
    return {
        "item_kind": "group",
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_by_user_id": group.created_by_user_id,
        "workspace_root": group.workspace_root,
        "created_at": group.created_at.isoformat(),
        "updated_at": group.updated_at.isoformat(),
    }


def _serialize_membership(membership: GroupMembership) -> dict[str, Any]:
    return {
        "item_kind": "membership",
        "id": membership.id,
        "group_id": membership.group_id,
        "user_id": membership.user_id,
        "agent_id": membership.agent_id,
        "member_kind": membership.member_kind.value,
        "role": membership.role.value,
        "is_enabled": membership.is_enabled,
        "created_at": membership.created_at.isoformat(),
        "updated_at": membership.updated_at.isoformat(),
    }


def _required_int(value: Any, *, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"A valid {label} is required.") from error


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return _required_int(value, label="member ID")


def _optional_text(payload: Mapping[str, Any], key: str) -> str | None:
    if key not in payload:
        return None
    value = payload.get(key)
    return None if value is None else str(value)


def _optional_bool(payload: Mapping[str, Any], key: str) -> bool | None:
    if key not in payload or payload.get(key) is None:
        return None
    return bool(payload.get(key))


def _require_authenticated_user(context: ModuleViewContext) -> int:
    if context.user_id is None:
        raise ValueError("Authentication required.")
    return int(context.user_id)


def _view_from_command(command: CommandContribution) -> ViewContribution:
    return ViewContribution(
        module_id=command.module_id,
        action_id=str(command.metadata.get("collection_view_id") or command.module_id).removesuffix(".view"),
        view_id=str(command.metadata.get("collection_view_id") or ""),
        name=command.name,
        description=command.description,
        metadata=dict(command.metadata or {}),
    )
