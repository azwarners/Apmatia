from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import replace

from apmatia.core.workspaces import resolve_group_workspace_root
from .models import Group, GroupMemberKind, GroupMembership, GroupRole, User, UserId, utc_now
from .repositories import GroupMembershipRepository, GroupRepository, UserRepository
from .services import AccessControlService, GroupService, UserService


def _hash_password(password: str, scheme: str = "sha512") -> str:
    if scheme != "sha512":
        raise ValueError(f"Unsupported password scheme: {scheme}")

    salt = secrets.token_hex(16)
    digest = hashlib.sha512((salt + password).encode("utf-8")).hexdigest()
    return f"{scheme}${salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$", 2)
    if len(parts) != 3:
        return False

    scheme, salt, stored_digest = parts
    if scheme != "sha512":
        return False

    computed = hashlib.sha512((salt + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(stored_digest, computed)


def _normalize_member_kind(member_kind: GroupMemberKind | str | object) -> GroupMemberKind:
    if isinstance(member_kind, GroupMemberKind):
        return member_kind
    if hasattr(member_kind, "value"):
        candidate = getattr(member_kind, "value")
        if candidate is not None:
            return GroupMemberKind(str(candidate))
    return GroupMemberKind(str(member_kind))


class UserManager(UserService):
    """
    Core orchestration entrypoint for user lifecycle operations.

    Implementation is intentionally deferred while we lock domain contracts.
    """

    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    def create_user(self, username: str, password: str) -> User:
        clean_username = username.strip()
        if not clean_username:
            raise ValueError("Username cannot be empty.")
        if not password:
            raise ValueError("Password cannot be empty.")
        if self._user_repo.get_by_username(clean_username):
            raise ValueError(f"User already exists: {clean_username}")

        now = utc_now()
        user = User(
            id=None,
            username=clean_username,
            password_hash=_hash_password(password),
            created_at=now,
            updated_at=now,
        )
        user_id = self._user_repo.create(user)
        return replace(user, id=user_id)

    def verify_user(self, username: str, password: str) -> bool:
        clean_username = username.strip()
        if not clean_username or not password:
            return False

        user = self._user_repo.get_by_username(clean_username)
        if user is None or not user.is_enabled:
            return False

        return _verify_password(password, user.password_hash)

    def set_user_enabled(self, user_id: UserId, enabled: bool) -> User:
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        updated = replace(user, is_enabled=enabled, updated_at=utc_now())
        self._user_repo.update(updated)
        return updated

    def edit_user(
        self,
        user_id: UserId,
        username: str | None = None,
        password: str | None = None,
        is_enabled: bool | None = None,
    ) -> User:
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        next_username = user.username
        if username is not None:
            trimmed = username.strip()
            if not trimmed:
                raise ValueError("Username cannot be empty.")
            existing = self._user_repo.get_by_username(trimmed)
            if existing and existing.id != user_id:
                raise ValueError(f"User already exists: {trimmed}")
            next_username = trimmed

        next_hash = user.password_hash
        if password is not None:
            if not password:
                raise ValueError("Password cannot be empty.")
            next_hash = _hash_password(password)

        next_enabled = user.is_enabled if is_enabled is None else is_enabled
        updated = replace(
            user,
            username=next_username,
            password_hash=next_hash,
            is_enabled=next_enabled,
            updated_at=utc_now(),
        )
        self._user_repo.update(updated)
        return updated

    def delete_user(self, user_id: UserId) -> bool:
        return self._user_repo.delete(user_id)

    def list_users(self) -> list[User]:
        return self._user_repo.list_all()


class GroupManager(GroupService):
    """
    Core orchestration entrypoint for group and membership operations.

    Implementation is intentionally deferred while we lock domain contracts.
    """

    def __init__(self, group_repo: GroupRepository, membership_repo: GroupMembershipRepository):
        self._group_repo = group_repo
        self._membership_repo = membership_repo

    def create_group(
        self,
        name: str,
        created_by_user_id: UserId,
        description: str = "",
        workspace_root: str = "",
    ) -> Group:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Group name cannot be empty.")
        if self._group_repo.get_by_name(clean_name):
            raise ValueError(f"Group already exists: {clean_name}")

        now = utc_now()
        group = Group(
            id=None,
            name=clean_name,
            description=description.strip(),
            created_by_user_id=created_by_user_id,
            workspace_root=str(workspace_root or ""),
            created_at=now,
            updated_at=now,
        )
        group_id = self._group_repo.create(group)
        created = replace(group, id=group_id)
        if not str(created.workspace_root).strip():
            created = replace(created, workspace_root=str(resolve_group_workspace_root(created)))
            self._group_repo.update(created)

        owner_membership = GroupMembership(
            id=None,
            group_id=group_id,
            user_id=created_by_user_id,
            role=GroupRole.OWNER,
            created_at=now,
            updated_at=now,
        )
        self._membership_repo.create(owner_membership)
        return created

    def edit_group(
        self,
        group_id: int,
        name: str | None = None,
        description: str | None = None,
        workspace_root: str | None = None,
    ) -> Group:
        group = self._group_repo.get_by_id(group_id)
        if group is None:
            raise ValueError(f"Group not found: {group_id}")

        next_name = group.name
        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise ValueError("Group name cannot be empty.")
            existing = self._group_repo.get_by_name(clean_name)
            if existing and existing.id != group_id:
                raise ValueError(f"Group already exists: {clean_name}")
            next_name = clean_name

        next_description = group.description if description is None else description.strip()
        updated = replace(
            group,
            name=next_name,
            description=next_description,
            workspace_root=group.workspace_root if workspace_root is None else workspace_root,
            updated_at=utc_now(),
        )
        if not str(updated.workspace_root).strip():
            updated = replace(updated, workspace_root=str(resolve_group_workspace_root(updated)))
        self._group_repo.update(updated)
        return updated

    def delete_group(self, group_id: int) -> bool:
        return self._group_repo.delete(group_id)

    def list_groups(self) -> list[Group]:
        return self._group_repo.list_all()

    def add_member(
        self,
        group_id: int,
        user_id: UserId | None = None,
        role: GroupRole = GroupRole.MEMBER,
        *,
        agent_id: int | None = None,
        member_kind: GroupMemberKind | str = GroupMemberKind.USER,
    ) -> GroupMembership:
        group = self._group_repo.get_by_id(group_id)
        if group is None:
            raise ValueError(f"Group not found: {group_id}")

        normalized_member_kind = _normalize_member_kind(member_kind)

        if normalized_member_kind == GroupMemberKind.AGENT:
            if agent_id is None:
                raise ValueError("Agent ID is required for agent memberships.")
            if role == GroupRole.OWNER:
                raise ValueError("Agent memberships cannot be group owners.")
            existing = self._membership_repo.find(
                group_id=group_id,
                agent_id=agent_id,
                member_kind=GroupMemberKind.AGENT,
            )
        else:
            if user_id is None:
                raise ValueError("User ID is required for user memberships.")
            existing = self._membership_repo.find(
                group_id=group_id,
                user_id=user_id,
                member_kind=GroupMemberKind.USER,
            )

        now = utc_now()
        if existing is not None:
            updated = replace(existing, role=role, is_enabled=True, updated_at=now)
            self._membership_repo.update(updated)
            return updated

        membership = GroupMembership(
            id=None,
            group_id=group_id,
            user_id=user_id,
            agent_id=agent_id,
            member_kind=normalized_member_kind,
            role=role,
            is_enabled=True,
            created_at=now,
            updated_at=now,
        )
        membership_id = self._membership_repo.create(membership)
        return replace(membership, id=membership_id)

    def set_membership_enabled(self, membership_id: int, enabled: bool) -> GroupMembership:
        membership = self._membership_repo.get_by_id(membership_id)
        if membership is None:
            raise ValueError(f"Membership not found: {membership_id}")

        updated = replace(membership, is_enabled=enabled, updated_at=utc_now())
        self._membership_repo.update(updated)
        return updated

    def list_group_members(self, group_id: int) -> list[GroupMembership]:
        return self._membership_repo.list_by_group(group_id)

    def list_user_groups(self, user_id: int) -> list[GroupMembership]:
        return self._membership_repo.list_by_user(user_id)


class AccessController(AccessControlService):
    """
    Core authorization policy entrypoint for UID/GID access checks.

    Implementation is intentionally deferred while we lock domain contracts.
    """

    def __init__(self, membership_repo: GroupMembershipRepository):
        self._membership_repo = membership_repo

    def can_read_private(self, owner_user_id: UserId, actor_user_id: UserId) -> bool:
        return owner_user_id == actor_user_id

    def can_read_group(self, group_id: int, actor_user_id: UserId) -> bool:
        membership = self._membership_repo.find(group_id=group_id, user_id=actor_user_id)
        return membership is not None and membership.is_enabled

    def can_write_group(self, group_id: int, actor_user_id: UserId) -> bool:
        membership = self._membership_repo.find(group_id=group_id, user_id=actor_user_id)
        return membership is not None and membership.is_enabled
