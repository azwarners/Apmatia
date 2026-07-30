from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from apmatia.core.models import ApmatiaObject, utc_now


TOPIC_STATUSES = {"active", "evolving", "closed", "archived"}
DISCUSSION_STATUSES = {"active", "paused", "closed", "archived"}
DISCUSSION_AGENT_MODES = {"discussion", "agentic"}
PARTICIPANT_ROLES = {"agent", "coordinator", "reviewer", "observer"}
PARTICIPANT_TURN_POLICIES = {"manual", "auto", "round_robin", "coordinator_only"}
SUMMARY_REASONS = {"topic_closed", "topic_evolved", "user_requested", "maintenance"}


def _normalize_text_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _normalize_status(value: Any, allowed: set[str], *, default: str) -> str:
    candidate = str(value or default).strip().lower()
    if candidate not in allowed:
        return default
    return candidate


def _normalize_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _normalize_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _normalize_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=utc_now().tzinfo)
    return datetime.fromisoformat(str(value))


@dataclass(slots=True)
class Topic(ApmatiaObject):
    title: str = ""
    description: str = ""
    status: str = "active"
    owner_agent_id: int | None = None
    parent_topic_id: str | int | None = None
    summary_id: str | int | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.title = str(self.title).strip()
        self.description = str(self.description).strip()
        self.status = _normalize_status(self.status, TOPIC_STATUSES, default="active")
        self.owner_agent_id = _normalize_int(self.owner_agent_id)
        self.tags = _normalize_text_list(self.tags)
        self.metadata = dict(self.metadata or {})


@dataclass(slots=True)
class Discussion(ApmatiaObject):
    topic_id: str | int | None = None
    title: str = ""
    status: str = "active"
    summary_id: str | int | None = None
    started_at: datetime | None = None
    last_activity_at: datetime | None = None
    closed_at: datetime | None = None
    agent_mode: str = "discussion"
    owner_user_id: int | None = None
    focused_wiki_id: str | int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.topic_id = self.topic_id if self.topic_id in (None, "") else str(self.topic_id)
        self.title = str(self.title).strip()
        self.status = _normalize_status(self.status, DISCUSSION_STATUSES, default="active")
        self.summary_id = self.summary_id if self.summary_id in (None, "") else str(self.summary_id)
        self.started_at = _normalize_datetime(self.started_at)
        self.last_activity_at = _normalize_datetime(self.last_activity_at)
        self.closed_at = _normalize_datetime(self.closed_at)
        self.agent_mode = _normalize_status(self.agent_mode, DISCUSSION_AGENT_MODES, default="discussion")
        self.owner_user_id = _normalize_int(self.owner_user_id)
        self.focused_wiki_id = self.focused_wiki_id if self.focused_wiki_id in (None, "") else str(self.focused_wiki_id)
        self.metadata = dict(self.metadata or {})


@dataclass(slots=True)
class DiscussionParticipant(ApmatiaObject):
    discussion_id: str | int | None = None
    agent_id: int | None = None
    group_id: str | int | None = None
    role: str = "agent"
    selected_model_id: int | None = None
    turn_policy: str = "round_robin"
    temperature_override: float | None = None
    tool_restrictions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.discussion_id = self.discussion_id if self.discussion_id in (None, "") else str(self.discussion_id)
        self.agent_id = _normalize_int(self.agent_id)
        self.group_id = self.group_id if self.group_id in (None, "") else str(self.group_id)
        self.role = _normalize_status(self.role, PARTICIPANT_ROLES, default="agent")
        self.selected_model_id = _normalize_int(self.selected_model_id)
        self.turn_policy = _normalize_status(self.turn_policy, PARTICIPANT_TURN_POLICIES, default="round_robin")
        self.temperature_override = _normalize_float(self.temperature_override)
        self.tool_restrictions = _normalize_text_list(self.tool_restrictions)
        self.metadata = dict(self.metadata or {})


@dataclass(slots=True)
class TopicSummary(ApmatiaObject):
    topic_id: str | int | None = None
    discussion_id: str | int | None = None
    reason: str = "maintenance"
    title: str = ""
    body: str = ""
    created_by_agent_id: int | None = None
    source_turn_ids: list[str | int] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.topic_id = self.topic_id if self.topic_id in (None, "") else str(self.topic_id)
        self.discussion_id = self.discussion_id if self.discussion_id in (None, "") else str(self.discussion_id)
        self.reason = _normalize_status(self.reason, SUMMARY_REASONS, default="maintenance")
        self.title = str(self.title).strip()
        self.body = str(self.body).strip()
        self.created_by_agent_id = _normalize_int(self.created_by_agent_id)
        self.source_turn_ids = [
            str(turn_id).strip()
            for turn_id in self.source_turn_ids
            if str(turn_id).strip()
        ]
        self.metadata = dict(self.metadata or {})


@dataclass(slots=True)
class DiscussionTurn(ApmatiaObject):
    topic_id: str | int | None = None
    discussion_id: str | int | None = None
    participant_id: str | int | None = None
    speaker_agent_id: int | None = None
    selected_model_id: int | None = None
    turn_index: int = 0
    turn_kind: str = "assistant"
    content: str = ""
    tool_name: str | None = None
    tool_status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.topic_id = self.topic_id if self.topic_id in (None, "") else str(self.topic_id)
        self.discussion_id = self.discussion_id if self.discussion_id in (None, "") else str(self.discussion_id)
        self.participant_id = self.participant_id if self.participant_id in (None, "") else str(self.participant_id)
        self.speaker_agent_id = _normalize_int(self.speaker_agent_id)
        self.selected_model_id = _normalize_int(self.selected_model_id)
        self.turn_index = max(0, int(self.turn_index))
        self.turn_kind = str(self.turn_kind or "assistant").strip().lower() or "assistant"
        self.content = str(self.content).strip()
        self.tool_name = None if self.tool_name in (None, "") else str(self.tool_name).strip()
        self.tool_status = None if self.tool_status in (None, "") else str(self.tool_status).strip()
        self.metadata = dict(self.metadata or {})


@dataclass(frozen=True, slots=True)
class TopicTransitionDecision:
    decision: str
    source: str
    confidence: float
    reason: str
    suggested_topic_title: str | None = None
