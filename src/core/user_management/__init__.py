"""Core user/group management design skeleton."""

from src.core.user_management.models import (
    Group,
    GroupId,
    GroupMembership,
    GroupRole,
    MembershipId,
    PasswordScheme,
    User,
    UserId,
)
from src.core.user_management.module import AccessController, GroupManager, UserManager
from src.core.user_management.repositories import (
    GroupMembershipRepository,
    GroupRepository,
    UserRepository,
)
from src.core.user_management.services import AccessControlService, GroupService, UserService

try:
    from src.core.user_management.sqlite_repositories import (
        SQLiteGroupMembershipRepository,
        SQLiteGroupRepository,
        SQLiteUserManagementBundle,
        SQLiteUserRepository,
        UserManagementTables,
    )
except ModuleNotFoundError:
    SQLiteGroupMembershipRepository = None
    SQLiteGroupRepository = None
    SQLiteUserManagementBundle = None
    SQLiteUserRepository = None
    UserManagementTables = None

__all__ = [
    "AccessControlService",
    "AccessController",
    "Group",
    "GroupId",
    "GroupManager",
    "GroupMembership",
    "GroupMembershipRepository",
    "GroupRepository",
    "GroupRole",
    "GroupService",
    "MembershipId",
    "PasswordScheme",
    "User",
    "UserId",
    "UserManager",
    "UserRepository",
    "UserService",
]

if SQLiteUserRepository is not None:
    __all__.extend(
        [
            "SQLiteGroupMembershipRepository",
            "SQLiteGroupRepository",
            "SQLiteUserManagementBundle",
            "SQLiteUserRepository",
            "UserManagementTables",
        ]
    )
