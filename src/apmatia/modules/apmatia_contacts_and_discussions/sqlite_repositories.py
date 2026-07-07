from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from persistence import SQLiteStore
except ModuleNotFoundError:
    from apmatia.lib.persistence.persistence import SQLiteStore

from .models import Discussion, DiscussionParticipant, DiscussionTurn, Topic, TopicSummary
from .repositories import (
    DiscussionParticipantRepository,
    DiscussionRepository,
    DiscussionTurnRepository,
    TopicRepository,
    TopicSummaryRepository,
)


@dataclass(frozen=True, slots=True)
class TopicManagementTables:
    topics: str = "topic_management_topics"
    discussions: str = "topic_management_discussions"
    participants: str = "topic_management_participants"
    summaries: str = "topic_management_summaries"
    turns: str = "topic_management_turns"


class SQLiteTopicRepository(TopicRepository):
    def __init__(self, store: SQLiteStore, tables: TopicManagementTables):
        self._store = store
        self._tables = tables

    def create(self, topic: Topic) -> int:
        return self._store.insert(self._tables.topics, _topic_payload(topic))

    def get(self, topic_id: str | int) -> Topic | None:
        row = self._store.get(self._tables.topics, id=topic_id)
        return None if row is None else _row_to_topic(row)

    def list_all(self) -> list[Topic]:
        return [_row_to_topic(row) for row in self._store.find(self._tables.topics)]

    def update(self, topic: Topic) -> None:
        if topic.id is None:
            raise ValueError("Cannot update topic without an id.")
        self._store.update(self._tables.topics, {"id": topic.id}, _topic_payload(topic))

    def delete(self, topic_id: str | int) -> bool:
        return self._store.delete(self._tables.topics, id=topic_id) > 0


class SQLiteDiscussionRepository(DiscussionRepository):
    def __init__(self, store: SQLiteStore, tables: TopicManagementTables):
        self._store = store
        self._tables = tables

    def create(self, discussion: Discussion) -> int:
        return self._store.insert(self._tables.discussions, _discussion_payload(discussion))

    def get(self, discussion_id: str | int) -> Discussion | None:
        row = self._store.get(self._tables.discussions, id=discussion_id)
        return None if row is None else _row_to_discussion(row)

    def list_all(self) -> list[Discussion]:
        return [_row_to_discussion(row) for row in self._store.find(self._tables.discussions)]

    def list_by_topic(self, topic_id: str | int) -> list[Discussion]:
        return [
            _row_to_discussion(row)
            for row in self._store.find(self._tables.discussions, topic_id=topic_id)
        ]

    def update(self, discussion: Discussion) -> None:
        if discussion.id is None:
            raise ValueError("Cannot update discussion without an id.")
        self._store.update(self._tables.discussions, {"id": discussion.id}, _discussion_payload(discussion))

    def delete(self, discussion_id: str | int) -> bool:
        return self._store.delete(self._tables.discussions, id=discussion_id) > 0


class SQLiteDiscussionParticipantRepository(DiscussionParticipantRepository):
    def __init__(self, store: SQLiteStore, tables: TopicManagementTables):
        self._store = store
        self._tables = tables

    def create(self, participant: DiscussionParticipant) -> int:
        return self._store.insert(self._tables.participants, _participant_payload(participant))

    def get(self, participant_id: str | int) -> DiscussionParticipant | None:
        row = self._store.get(self._tables.participants, id=participant_id)
        return None if row is None else _row_to_participant(row)

    def list_all(self) -> list[DiscussionParticipant]:
        return [_row_to_participant(row) for row in self._store.find(self._tables.participants)]

    def list_by_discussion(self, discussion_id: str | int) -> list[DiscussionParticipant]:
        return [
            _row_to_participant(row)
            for row in self._store.find(self._tables.participants, discussion_id=discussion_id)
        ]

    def update(self, participant: DiscussionParticipant) -> None:
        if participant.id is None:
            raise ValueError("Cannot update participant without an id.")
        self._store.update(self._tables.participants, {"id": participant.id}, _participant_payload(participant))

    def delete(self, participant_id: str | int) -> bool:
        return self._store.delete(self._tables.participants, id=participant_id) > 0


class SQLiteTopicSummaryRepository(TopicSummaryRepository):
    def __init__(self, store: SQLiteStore, tables: TopicManagementTables):
        self._store = store
        self._tables = tables

    def create(self, summary: TopicSummary) -> int:
        return self._store.insert(self._tables.summaries, _summary_payload(summary))

    def get(self, summary_id: str | int) -> TopicSummary | None:
        row = self._store.get(self._tables.summaries, id=summary_id)
        return None if row is None else _row_to_summary(row)

    def list_all(self) -> list[TopicSummary]:
        return [_row_to_summary(row) for row in self._store.find(self._tables.summaries)]

    def list_by_topic(self, topic_id: str | int) -> list[TopicSummary]:
        return [
            _row_to_summary(row)
            for row in self._store.find(self._tables.summaries, topic_id=topic_id)
        ]

    def update(self, summary: TopicSummary) -> None:
        if summary.id is None:
            raise ValueError("Cannot update summary without an id.")
        self._store.update(self._tables.summaries, {"id": summary.id}, _summary_payload(summary))

    def delete(self, summary_id: str | int) -> bool:
        return self._store.delete(self._tables.summaries, id=summary_id) > 0


class SQLiteDiscussionTurnRepository(DiscussionTurnRepository):
    def __init__(self, store: SQLiteStore, tables: TopicManagementTables):
        self._store = store
        self._tables = tables

    def create(self, turn: DiscussionTurn) -> int:
        return self._store.insert(self._tables.turns, _turn_payload(turn))

    def get(self, turn_id: str | int) -> DiscussionTurn | None:
        row = self._store.get(self._tables.turns, id=turn_id)
        return None if row is None else _row_to_turn(row)

    def list_all(self) -> list[DiscussionTurn]:
        return [_row_to_turn(row) for row in self._store.find(self._tables.turns)]

    def list_by_discussion(self, discussion_id: str | int) -> list[DiscussionTurn]:
        return [
            _row_to_turn(row)
            for row in self._store.find(self._tables.turns, discussion_id=discussion_id)
        ]

    def update(self, turn: DiscussionTurn) -> None:
        if turn.id is None:
            raise ValueError("Cannot update turn without an id.")
        self._store.update(self._tables.turns, {"id": turn.id}, _turn_payload(turn))

    def delete(self, turn_id: str | int) -> bool:
        return self._store.delete(self._tables.turns, id=turn_id) > 0


class TopicManagementBundle:
    def __init__(self, store: SQLiteStore | str | Path, tables: TopicManagementTables | None = None):
        self.tables = tables or TopicManagementTables()
        self.store = SQLiteStore(store) if not isinstance(store, SQLiteStore) else store
        self.topics = SQLiteTopicRepository(self.store, self.tables)
        self.discussions = SQLiteDiscussionRepository(self.store, self.tables)
        self.participants = SQLiteDiscussionParticipantRepository(self.store, self.tables)
        self.summaries = SQLiteTopicSummaryRepository(self.store, self.tables)
        self.turns = SQLiteDiscussionTurnRepository(self.store, self.tables)


def _base_payload(obj: Any) -> dict[str, Any]:
    return {
        "id": obj.id,
        "owner_user_id": obj.owner_user_id,
        "owner_group_id": obj.owner_group_id,
        "mode": obj.mode,
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
    }


def _topic_payload(topic: Topic) -> dict[str, Any]:
    payload = _base_payload(topic)
    payload.update(
        {
            "title": topic.title,
            "description": topic.description,
            "status": topic.status,
            "owner_agent_id": topic.owner_agent_id,
            "parent_topic_id": topic.parent_topic_id,
            "summary_id": topic.summary_id,
            "tags": list(topic.tags),
            "metadata": dict(topic.metadata),
        }
    )
    return payload


def _discussion_payload(discussion: Discussion) -> dict[str, Any]:
    payload = _base_payload(discussion)
    payload.update(
        {
            "topic_id": discussion.topic_id,
            "title": discussion.title,
            "status": discussion.status,
            "summary_id": discussion.summary_id,
            "started_at": None if discussion.started_at is None else discussion.started_at.isoformat(),
            "last_activity_at": None if discussion.last_activity_at is None else discussion.last_activity_at.isoformat(),
            "closed_at": None if discussion.closed_at is None else discussion.closed_at.isoformat(),
            "metadata": dict(discussion.metadata),
        }
    )
    return payload


def _participant_payload(participant: DiscussionParticipant) -> dict[str, Any]:
    payload = _base_payload(participant)
    payload.update(
        {
            "discussion_id": participant.discussion_id,
            "agent_id": participant.agent_id,
            "group_id": participant.group_id,
            "role": participant.role,
            "selected_model_id": participant.selected_model_id,
            "turn_policy": participant.turn_policy,
            "temperature_override": participant.temperature_override,
            "tool_restrictions": list(participant.tool_restrictions),
            "metadata": dict(participant.metadata),
        }
    )
    return payload


def _summary_payload(summary: TopicSummary) -> dict[str, Any]:
    payload = _base_payload(summary)
    payload.update(
        {
            "topic_id": summary.topic_id,
            "discussion_id": summary.discussion_id,
            "reason": summary.reason,
            "title": summary.title,
            "body": summary.body,
            "created_by_agent_id": summary.created_by_agent_id,
            "source_turn_ids": list(summary.source_turn_ids),
            "metadata": dict(summary.metadata),
        }
    )
    return payload


def _turn_payload(turn: DiscussionTurn) -> dict[str, Any]:
    payload = _base_payload(turn)
    payload.update(
        {
            "topic_id": turn.topic_id,
            "discussion_id": turn.discussion_id,
            "participant_id": turn.participant_id,
            "speaker_agent_id": turn.speaker_agent_id,
            "selected_model_id": turn.selected_model_id,
            "turn_index": turn.turn_index,
            "turn_kind": turn.turn_kind,
            "content": turn.content,
            "tool_name": turn.tool_name,
            "tool_status": turn.tool_status,
            "metadata": dict(turn.metadata),
        }
    )
    return payload


def _row_to_topic(row: dict[str, Any]) -> Topic:
    return Topic(
        id=row.get("id"),
        owner_user_id=_parse_int(row.get("owner_user_id")),
        owner_group_id=_parse_int(row.get("owner_group_id")),
        mode=_parse_int(row.get("mode"), default=0) or 0,
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
        title=str(row.get("title", "")),
        description=str(row.get("description", "")),
        status=str(row.get("status", "active")),
        owner_agent_id=_parse_int(row.get("owner_agent_id")),
        parent_topic_id=row.get("parent_topic_id"),
        summary_id=row.get("summary_id"),
        tags=_parse_json_list(row.get("tags")),
        metadata=_parse_json_dict(row.get("metadata")),
    )


def _row_to_discussion(row: dict[str, Any]) -> Discussion:
    return Discussion(
        id=row.get("id"),
        owner_user_id=_parse_int(row.get("owner_user_id")),
        owner_group_id=_parse_int(row.get("owner_group_id")),
        mode=_parse_int(row.get("mode"), default=0) or 0,
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
        topic_id=row.get("topic_id"),
        title=str(row.get("title", "")),
        status=str(row.get("status", "active")),
        summary_id=row.get("summary_id"),
        started_at=_parse_datetime(row.get("started_at")),
        last_activity_at=_parse_datetime(row.get("last_activity_at")),
        closed_at=_parse_datetime(row.get("closed_at")),
        metadata=_parse_json_dict(row.get("metadata")),
    )


def _row_to_participant(row: dict[str, Any]) -> DiscussionParticipant:
    return DiscussionParticipant(
        id=row.get("id"),
        owner_user_id=_parse_int(row.get("owner_user_id")),
        owner_group_id=_parse_int(row.get("owner_group_id")),
        mode=_parse_int(row.get("mode"), default=0) or 0,
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
        discussion_id=row.get("discussion_id"),
        agent_id=_parse_int(row.get("agent_id")),
        group_id=row.get("group_id"),
        role=str(row.get("role", "agent")),
        selected_model_id=_parse_int(row.get("selected_model_id")),
        turn_policy=str(row.get("turn_policy", "manual")),
        temperature_override=_parse_float(row.get("temperature_override")),
        tool_restrictions=_parse_json_list(row.get("tool_restrictions")),
        metadata=_parse_json_dict(row.get("metadata")),
    )


def _row_to_summary(row: dict[str, Any]) -> TopicSummary:
    return TopicSummary(
        id=row.get("id"),
        owner_user_id=_parse_int(row.get("owner_user_id")),
        owner_group_id=_parse_int(row.get("owner_group_id")),
        mode=_parse_int(row.get("mode"), default=0) or 0,
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
        topic_id=row.get("topic_id"),
        discussion_id=row.get("discussion_id"),
        reason=str(row.get("reason", "maintenance")),
        title=str(row.get("title", "")),
        body=str(row.get("body", "")),
        created_by_agent_id=_parse_int(row.get("created_by_agent_id")),
        source_turn_ids=_parse_json_list(row.get("source_turn_ids")),
        metadata=_parse_json_dict(row.get("metadata")),
    )


def _row_to_turn(row: dict[str, Any]) -> DiscussionTurn:
    return DiscussionTurn(
        id=row.get("id"),
        owner_user_id=_parse_int(row.get("owner_user_id")),
        owner_group_id=_parse_int(row.get("owner_group_id")),
        mode=_parse_int(row.get("mode"), default=0) or 0,
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
        topic_id=row.get("topic_id"),
        discussion_id=row.get("discussion_id"),
        participant_id=row.get("participant_id"),
        speaker_agent_id=_parse_int(row.get("speaker_agent_id")),
        selected_model_id=_parse_int(row.get("selected_model_id")),
        turn_index=_parse_int(row.get("turn_index"), default=0) or 0,
        turn_kind=str(row.get("turn_kind", "assistant")),
        content=str(row.get("content", "")),
        tool_name=row.get("tool_name"),
        tool_status=row.get("tool_status"),
        metadata=_parse_json_dict(row.get("metadata")),
    )


def _parse_json_dict(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return dict(value)
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _parse_json_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item).strip()]


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _parse_int(value: Any, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
