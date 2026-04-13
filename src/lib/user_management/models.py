from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


UserId = int
GroupId = int
MembershipId = int


class PasswordScheme(str, Enum):
    SHA512 = "sha512"


class GroupRole(str, Enum):
    OWNER = "owner"
    MEMBER = "member"


@dataclass(slots=True)
class User:
    id: UserId | None
    username: str
    password_hash: str
    password_scheme: PasswordScheme = PasswordScheme.SHA512
    is_enabled: bool = True
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Group:
    id: GroupId | None
    name: str
    description: str = ""
    created_by_user_id: UserId | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class GroupMembership:
    id: MembershipId | None
    group_id: GroupId
    user_id: UserId
    role: GroupRole = GroupRole.MEMBER
    is_enabled: bool = True
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

