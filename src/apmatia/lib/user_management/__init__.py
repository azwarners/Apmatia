"""Core user/group management design skeleton."""

from .models import (
    Group,
    GroupId,
    GroupMembership,
    GroupRole,
    MembershipId,
    PasswordScheme,
    User,
    UserId,
)
from .module import AccessController, GroupManager, UserManager
from .repositories import (
    GroupMembershipRepository,
    GroupRepository,
    UserRepository,
)
from .services import AccessControlService, GroupService, UserService

try:
    from .sqlite_repositories import (
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
