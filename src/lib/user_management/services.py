from __future__ import annotations

from typing import Protocol

from .models import Group, GroupId, GroupMembership, GroupRole, MembershipId, User, UserId


class UserService(Protocol):
    def create_user(self, username: str, password: str) -> User:
        """Create and return a user record."""
        raise NotImplementedError

    def verify_user(self, username: str, password: str) -> bool:
        """Return True when provided credentials are valid."""
        raise NotImplementedError

    def set_user_enabled(self, user_id: UserId, enabled: bool) -> User:
        """Enable or disable a user and return updated record."""
        raise NotImplementedError

    def edit_user(
        self,
        user_id: UserId,
        username: str | None = None,
        password: str | None = None,
        is_enabled: bool | None = None,
    ) -> User:
        """Edit a user and return updated record."""
        raise NotImplementedError

    def delete_user(self, user_id: UserId) -> bool:
        """Delete a user by ID. Return True if removed."""
        raise NotImplementedError

    def list_users(self) -> list[User]:
        """List all users."""
        raise NotImplementedError


class GroupService(Protocol):
    def create_group(self, name: str, created_by_user_id: UserId, description: str = "") -> Group:
        """Create and return a group record."""
        raise NotImplementedError

    def delete_group(self, group_id: GroupId) -> bool:
        """Delete a group by ID. Return True if removed."""
        raise NotImplementedError

    def list_groups(self) -> list[Group]:
        """List all groups."""
        raise NotImplementedError

    def add_member(self, group_id: GroupId, user_id: UserId, role: GroupRole = GroupRole.MEMBER) -> GroupMembership:
        """Add a user to a group and return the membership."""
        raise NotImplementedError

    def set_membership_enabled(self, membership_id: MembershipId, enabled: bool) -> GroupMembership:
        """Enable or disable membership and return updated membership."""
        raise NotImplementedError

    def list_group_members(self, group_id: GroupId) -> list[GroupMembership]:
        """List memberships for a group."""
        raise NotImplementedError

    def list_user_groups(self, user_id: UserId) -> list[GroupMembership]:
        """List memberships for a user."""
        raise NotImplementedError


class AccessControlService(Protocol):
    def can_read_private(self, owner_user_id: UserId, actor_user_id: UserId) -> bool:
        """Return True if actor can read owner's private data."""
        raise NotImplementedError

    def can_read_group(self, group_id: GroupId, actor_user_id: UserId) -> bool:
        """Return True if actor can read group-scoped data."""
        raise NotImplementedError

    def can_write_group(self, group_id: GroupId, actor_user_id: UserId) -> bool:
        """Return True if actor can write group-scoped data."""
        raise NotImplementedError
