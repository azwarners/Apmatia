from __future__ import annotations

from typing import Protocol

from .models import Group, GroupId, GroupMembership, MembershipId, User, UserId

class UserRepository:
    def __init__(self, store: SQLiteStore, tables: UserManagementTables):
        self._store = store
        self._tables = tables

    def create(self, user: User) -> UserId:
        """Persist a new user and return its ID."""
        payload = {
            "username": user.username,
            "password_hash": user.password_hash,
            "password_scheme": user.password_scheme.value,
            "is_enabled": user.is_enabled,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
        return self._store.insert(self._tables.users, payload)

    def get_by_id(self, user_id: UserId) -> User | None:
        """Return a user by ID, or None if not found."""
        row = self._store.get(self._tables.users, id=user_id)
        if row is None:
            return None
        return self._row_to_user(row)

    def get_by_username(self, username: str) -> User | None:
        """Return a user by username, or None if not found."""
        row = self._store.get(self._tables.users, username=username)
        if row is None:
            return None
        return self._row_to_user(row)

    def update(self, user: User) -> None:
        """Persist an existing user."""
        if user.id is None:
            raise ValueError("Cannot update user without an id.")

        self._store.update(
            self._tables.users,
            where={"id": user.id},
            data={
                "username": user.username,
                "password_hash": user.password_hash,
                "password_scheme": user.password_scheme.value,
                "is_enabled": user.is_enabled,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            },
        )

    def delete(self, user_id: UserId) -> bool:
        """Delete a user by ID. Return True if a record was removed."""
        deleted = self._store.delete(self._tables.users, id=user_id)
        return deleted > 0

    def list_all(self) -> list[User]:
        """Return all users."""
        rows = self._store.find(self._tables.users)
        return [self._row_to_user(row) for row in rows]

    @staticmethod
    def _row_to_user(row: dict) -> User:
        return User(
            id=int(row["id"]),
            username=str(row["username"]),
            password_hash=str(row["password_hash"]),
            password_scheme=PasswordScheme(str(row.get("password_scheme", PasswordScheme.SHA512.value))),
            is_enabled=bool(row.get("is_enabled", True)),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
        )

class GroupRepository:
    def __init__(self, store: SQLiteStore, tables: UserManagementTables):
        self._store = store
        self._tables = tables

    def create(self, group: Group) -> GroupId:
        """Persist a new group and return its ID."""
        payload = {
            "name": group.name,
            "description": group.description,
            "created_by_user_id": group.created_by_user_id,
            "created_at": group.created_at.isoformat(),
            "updated_at": group.updated_at.isoformat(),
        }
        return self._store.insert(self._tables.groups, payload)

    def get_by_id(self, group_id: GroupId) -> Group | None:
        """Return a group by ID, or None if not found."""
        row = self._store.get(self._tables.groups, id=group_id)
        if row is None:
            return None
        return self._row_to_group(row)

    def get_by_name(self, name: str) -> Group | None:
        """Return a group by name, or None if not found."""
        row = self._store.get(self._tables.groups, name=name)
        if row is None:
            return None
        return self._row_to_group(row)

    def update(self, group: Group) -> None:
        """Persist an existing group."""
        if group.id is None:
            raise ValueError("Cannot update group without an id.")

        self._store.update(
            self._tables.groups,
            where={"id": group.id},
            data={
                "name": group.name,
                "description": group.description,
                "created_by_user_id": group.created_by_user_id,
                "created_at": group.created_at.isoformat(),
                "updated_at": group.updated_at.isoformat(),
            },
        )

    def delete(self, group_id: GroupId) -> bool:
        """Delete a group by ID. Return True if a record was removed."""
        deleted = self._store.delete(self._tables.groups, id=group_id)
        return deleted > 0

    def list_all(self) -> list[Group]:
        """Return all groups."""
        rows = self._store.find(self._tables.groups)
        return [self._row_to_group(row) for row in rows]

    @staticmethod
    def _row_to_group(row: dict) -> Group:
        created_by_user_id = row.get("created_by_user_id")
        return Group(
            id=int(row["id"]),
            name=str(row["name"]),
            description=str(row.get("description", "")),
            created_by_user_id=int(created_by_user_id) if created_by_user_id is not None else None,
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
        )

class GroupMembershipRepository:
    def __init__(self, store: SQLiteStore, tables: UserManagementTables):
        self._store = store
        self._tables = tables

    def create(self, membership: GroupMembership) -> MembershipId:
        """Persist a new membership and return its ID."""
        payload = {
            "group_id": membership.group_id,
            "user_id": membership.user_id,
            "role": membership.role.value,
            "is_enabled": membership.is_enabled,
            "created_at": membership.created_at.isoformat(),
            "updated_at": membership.updated_at.isoformat(),
        }
        return self._store.insert(self._tables.memberships, payload)

    def get_by_id(self, membership_id: MembershipId) -> GroupMembership | None:
        """Return a membership by ID, or None if not found."""
        row = self._store.get(self._tables.memberships, id=membership_id)
        if row is None:
            return None
        return self._row_to_membership(row)

    def find(self, group_id: GroupId, user_id: UserId) -> GroupMembership | None:
        """Return membership for a specific group/user pair, or None."""
        row = self._store.get(self._tables.memberships, group_id=group_id, user_id=user_id)
        if row is None:
            return None
        return self._row_to_membership(row)

    def update(self, membership: GroupMembership) -> None:
        """Persist an existing membership."""
        if membership.id is None:
            raise ValueError("Cannot update membership without an id.")

        self._store.update(
            self._tables.memberships,
            where={"id": membership.id},
            data={
                "group_id": membership.group_id,
                "user_id": membership.user_id,
                "role": membership.role.value,
                "is_enabled": membership.is_enabled,
                "created_at": membership.created_at.isoformat(),
                "updated_at": membership.updated_at.isoformat(),
            },
        )

    def list_by_group(self, group_id: GroupId) -> list[GroupMembership]:
        """Return memberships for a group."""
        rows = self._store.find(self._tables.memberships, group_id=group_id)
        return [self._row_to_membership(row) for row in rows]

    def list_by_user(self, user_id: UserId) -> list[GroupMembership]:
        """Return memberships for a user."""
        rows = self._store.find(self._tables.memberships, user_id=user_id)
        return [self._row_to_membership(row) for row in rows]

    @staticmethod
    def _row_to_membership(row: dict) -> GroupMembership:
        return GroupMembership(
            id=int(row["id"]),
            group_id=int(row["group_id"]),
            user_id=int(row["user_id"]),
            role=GroupRole(str(row.get("role", GroupRole.MEMBER.value))),
            is_enabled=bool(row.get("is_enabled", True)),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
        )
