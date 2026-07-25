"""Stable user, group, membership, and authentication infrastructure."""

from .auth import AuthSession, SessionManager
from .manager import AccessController, GroupManager, UserManager
from .models import (
    Group,
    GroupId,
    GroupMemberKind,
    GroupMembership,
    GroupRole,
    MembershipId,
    PasswordScheme,
    User,
    UserId,
)
from .repositories import GroupMembershipRepository, GroupRepository, UserRepository
from .services import AccessControlService, GroupService, UserService
from .sqlite_repositories import (
    SQLiteGroupMembershipRepository,
    SQLiteGroupRepository,
    SQLiteUserManagementBundle,
    SQLiteUserRepository,
    UserManagementTables,
)

__all__ = [
    "AccessControlService",
    "AccessController",
    "AuthSession",
    "Group",
    "GroupId",
    "GroupManager",
    "GroupMemberKind",
    "GroupMembership",
    "GroupMembershipRepository",
    "GroupRepository",
    "GroupRole",
    "GroupService",
    "MembershipId",
    "PasswordScheme",
    "SessionManager",
    "SQLiteGroupMembershipRepository",
    "SQLiteGroupRepository",
    "SQLiteUserManagementBundle",
    "SQLiteUserRepository",
    "User",
    "UserId",
    "UserManagementTables",
    "UserManager",
    "UserRepository",
    "UserService",
]
