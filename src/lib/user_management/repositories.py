from __future__ import annotations

from typing import Protocol

from .models import Group, GroupId, GroupMembership, MembershipId, User, UserId


class UserRepository(Protocol):
    def create(self, user: User) -> UserId:
        """Persist a new user and return its ID."""
        raise NotImplementedError

    def get_by_id(self, user_id: UserId) -> User | None:
        """Return a user by ID, or None if not found."""
        raise NotImplementedError

    def get_by_username(self, username: str) -> User | None:
        """Return a user by username, or None if not found."""
        raise NotImplementedError

    def update(self, user: User) -> None:
        """Persist an existing user."""
        raise NotImplementedError

    def delete(self, user_id: UserId) -> bool:
        """Delete a user by ID. Return True if a record was removed."""
        raise NotImplementedError

    def list_all(self) -> list[User]:
        """Return all users."""
        raise NotImplementedError


class GroupRepository(Protocol):
    def create(self, group: Group) -> GroupId:
        """Persist a new group and return its ID."""
        raise NotImplementedError

    def get_by_id(self, group_id: GroupId) -> Group | None:
        """Return a group by ID, or None if not found."""
        raise NotImplementedError

    def get_by_name(self, name: str) -> Group | None:
        """Return a group by name, or None if not found."""
        raise NotImplementedError

    def update(self, group: Group) -> None:
        """Persist an existing group."""
        raise NotImplementedError

    def delete(self, group_id: GroupId) -> bool:
        """Delete a group by ID. Return True if a record was removed."""
        raise NotImplementedError

    def list_all(self) -> list[Group]:
        """Return all groups."""
        raise NotImplementedError


class GroupMembershipRepository(Protocol):
    def create(self, membership: GroupMembership) -> MembershipId:
        """Persist a new membership and return its ID."""
        raise NotImplementedError

    def get_by_id(self, membership_id: MembershipId) -> GroupMembership | None:
        """Return a membership by ID, or None if not found."""
        raise NotImplementedError

    def find(self, group_id: GroupId, user_id: UserId) -> GroupMembership | None:
        """Return membership for a specific group/user pair, or None."""
        raise NotImplementedError

    def update(self, membership: GroupMembership) -> None:
        """Persist an existing membership."""
        raise NotImplementedError

    def list_by_group(self, group_id: GroupId) -> list[GroupMembership]:
        """Return memberships for a group."""
        raise NotImplementedError

    def list_by_user(self, user_id: UserId) -> list[GroupMembership]:
        """Return memberships for a user."""
        raise NotImplementedError
