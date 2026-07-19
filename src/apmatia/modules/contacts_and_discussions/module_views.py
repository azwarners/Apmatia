from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from typing import Any

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution
from apmatia.lib.apmatia_core.models import utc_now
from apmatia.lib.model_management import LLMManager

from .models import Discussion, DiscussionParticipant, DiscussionTurn, Topic, TopicSummary
from .services import TopicManagementService


class ApmatiaTopicManagementModuleViewProvider:
    def __init__(self, service: TopicManagementService | None = None):
        self._service = service or TopicManagementService()

    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        object_type = _object_type(view.metadata)
        if object_type == "topic":
            items = [item for item in self._service.list_topics() if _is_visible(item, context=context)]
            items = sorted(items, key=_topic_sort_key, reverse=True)
            return [_serialize_topic(item) for item in items]
        if object_type == "discussion":
            items = [item for item in self._service.list_discussions() if _is_visible(item, context=context)]
            items = sorted(items, key=_discussion_sort_key, reverse=True)
            return [_serialize_discussion(item, service=self._service) for item in items]
        if object_type == "participant":
            items = _build_recent_chat_roster(self._service, context=context)
            return items
        if object_type == "summary":
            items = [item for item in self._service.list_summaries() if _is_visible(item, context=context)]
            items = sorted(items, key=_summary_sort_key, reverse=True)
            return [_serialize_summary(item) for item in items]
        if object_type == "turn":
            items = [item for item in self._service.list_turns() if _is_visible(item, context=context)]
            items = sorted(items, key=_turn_sort_key, reverse=True)
            return [_serialize_turn(item, service=self._service) for item in items]
        raise ValueError(f"Unsupported topic management object type: {object_type}")

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        metadata = dict(command.metadata or {})
        object_type = _object_type(metadata)
        verb = str(metadata.get("verb") or "").strip().lower() or _command_verb(command.command_id)

        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command), context=context)}
        if object_type == "topic" and verb == "assess_transition":
            return self._assess_transition(payload)
        if object_type == "topic" and verb == "summarize":
            return self._summarize_topic(payload, context=context)
        if verb == "create":
            return self._create_object(object_type, payload=payload, context=context)
        if verb == "edit":
            return self._edit_object(object_type, payload=payload, context=context)
        if verb == "delete":
            return self._delete_object(object_type, payload=payload, context=context)
        raise ValueError(f"Unsupported module command verb for now: {verb}")

    def _create_object(
        self,
        object_type: str,
        *,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any]:
        if object_type == "topic":
            topic = Topic(
                title=str(payload.get("title") or "").strip(),
                description=str(payload.get("description") or "").strip(),
                status=str(payload.get("status") or "active"),
                owner_agent_id=_optional_int(payload.get("owner_agent_id")),
                parent_topic_id=_optional_text(payload.get("parent_topic_id")),
                summary_id=_optional_text(payload.get("summary_id")),
                tags=_parse_tags(payload.get("tags")),
                metadata=_parse_mapping(payload.get("metadata")),
            )
            topic.owner_user_id = context.user_id
            topic.owner_group_id = next(iter(context.group_ids), None)
            created = self._service.create_topic(topic)
            return {"status": "created", "item": _serialize_topic(created)}

        if object_type == "discussion":
            discussion = Discussion(
                topic_id=_required_text(payload.get("topic_id"), field_name="topic_id"),
                title=str(payload.get("title") or "").strip(),
                status=str(payload.get("status") or "active"),
                summary_id=_optional_text(payload.get("summary_id")),
                started_at=payload.get("started_at"),
                metadata=_parse_mapping(payload.get("metadata")),
            )
            discussion.owner_user_id = context.user_id
            discussion.owner_group_id = next(iter(context.group_ids), None)
            created = self._service.create_discussion(discussion)
            return {"status": "created", "item": _serialize_discussion(created)}

        if object_type == "participant":
            target_kind, target_value = _parse_participant_target(payload)
            participant = DiscussionParticipant(
                discussion_id=_optional_text(payload.get("discussion_id")),
                agent_id=_optional_int(target_value) if target_kind == "agent" else None,
                group_id=_optional_text(target_value) if target_kind == "group" else None,
                role=str(payload.get("role") or "agent"),
                selected_model_id=_optional_int(payload.get("selected_model_id")),
                turn_policy=str(payload.get("turn_policy") or "round_robin"),
                temperature_override=payload.get("temperature_override"),
                tool_restrictions=_parse_tags(payload.get("tool_restrictions")),
                metadata=_parse_mapping(payload.get("metadata")),
            )
            participant.owner_user_id = context.user_id
            participant.owner_group_id = next(iter(context.group_ids), None)
            created = self._service.create_participant(participant)
            return {"status": "created", "item": _serialize_participant(created)}

        if object_type == "summary":
            discussion_id = _optional_text(payload.get("discussion_id"))
            topic_id = _optional_text(payload.get("topic_id"))
            if not _summary_has_participants(self._service, topic_id=topic_id, discussion_id=discussion_id):
                raise ValueError("Select participants before creating a topic summary.")
            summary = TopicSummary(
                topic_id=_required_text(payload.get("topic_id"), field_name="topic_id"),
                discussion_id=discussion_id,
                reason=str(payload.get("reason") or "maintenance"),
                title=str(payload.get("title") or "").strip(),
                body=str(payload.get("body") or "").strip(),
                created_by_agent_id=_optional_int(payload.get("created_by_agent_id")),
                source_turn_ids=_parse_ids(payload.get("source_turn_ids")),
                metadata=_parse_mapping(payload.get("metadata")),
                created_at=utc_now(),
            )
            summary.owner_user_id = context.user_id
            summary.owner_group_id = next(iter(context.group_ids), None)
            created = self._service.create_summary(summary)
            return {"status": "created", "item": _serialize_summary(created)}

        if object_type == "turn":
            turn = DiscussionTurn(
                topic_id=_required_text(payload.get("topic_id"), field_name="topic_id"),
                discussion_id=_required_text(payload.get("discussion_id"), field_name="discussion_id"),
                participant_id=_optional_text(payload.get("participant_id")),
                speaker_agent_id=_optional_int(payload.get("speaker_agent_id")),
                selected_model_id=_optional_int(payload.get("selected_model_id")),
                turn_index=_optional_int(payload.get("turn_index"), default=0) or 0,
                turn_kind=str(payload.get("turn_kind") or "assistant"),
                content=str(payload.get("content") or "").strip(),
                tool_name=_optional_text(payload.get("tool_name")),
                tool_status=_optional_text(payload.get("tool_status")),
                metadata=_parse_mapping(payload.get("metadata")),
            )
            turn.owner_user_id = context.user_id
            turn.owner_group_id = next(iter(context.group_ids), None)
            created = self._service.record_turn(turn)
            return {"status": "created", "item": _serialize_turn(created)}

        raise ValueError(f"Unsupported topic management object type: {object_type}")

    def _edit_object(
        self,
        object_type: str,
        *,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any]:
        item_id = _required_text(payload.get("item_id"), field_name="item_id")
        if object_type == "topic":
            current = _require_topic(self._service, item_id)
            updated = replace(
                current,
                title=_maybe_str(payload, "title", current.title),
                description=_maybe_str(payload, "description", current.description),
                status=_maybe_str(payload, "status", current.status),
                owner_agent_id=_maybe_int(payload, "owner_agent_id", current.owner_agent_id),
                parent_topic_id=_maybe_str(payload, "parent_topic_id", current.parent_topic_id),
                summary_id=_maybe_str(payload, "summary_id", current.summary_id),
                tags=_maybe_tags(payload, "tags", current.tags),
                metadata=_maybe_mapping(payload, "metadata", current.metadata),
                updated_at=utc_now(),
            )
            self._service.bundle.topics.update(updated)
            return {"status": "updated", "item": _serialize_topic(updated)}

        if object_type == "discussion":
            current = _require_discussion(self._service, item_id)
            updated = replace(
                current,
                topic_id=_maybe_str(payload, "topic_id", current.topic_id),
                title=_maybe_str(payload, "title", current.title),
                status=_maybe_str(payload, "status", current.status),
                summary_id=_maybe_str(payload, "summary_id", current.summary_id),
                started_at=_maybe_dt(payload, "started_at", current.started_at),
                last_activity_at=_maybe_dt(payload, "last_activity_at", current.last_activity_at),
                closed_at=_maybe_dt(payload, "closed_at", current.closed_at),
                metadata=_maybe_mapping(payload, "metadata", current.metadata),
                updated_at=utc_now(),
            )
            self._service.bundle.discussions.update(updated)
            return {"status": "updated", "item": _serialize_discussion(updated)}

        if object_type == "participant":
            current = _require_participant(self._service, item_id)
            updated = replace(
                current,
                discussion_id=_maybe_str(payload, "discussion_id", current.discussion_id),
                agent_id=_maybe_int(payload, "agent_id", current.agent_id),
                group_id=_maybe_text(payload, "group_id", current.group_id),
                role=_maybe_str(payload, "role", current.role),
                selected_model_id=_maybe_int(payload, "selected_model_id", current.selected_model_id),
                turn_policy=_maybe_str(payload, "turn_policy", current.turn_policy),
                temperature_override=_maybe_float(payload, "temperature_override", current.temperature_override),
                tool_restrictions=_maybe_tags(payload, "tool_restrictions", current.tool_restrictions),
                metadata=_maybe_mapping(payload, "metadata", current.metadata),
                updated_at=utc_now(),
            )
            self._service.bundle.participants.update(updated)
            return {"status": "updated", "item": _serialize_participant(updated)}

        if object_type == "summary":
            current = _require_summary(self._service, item_id)
            updated = replace(
                current,
                topic_id=_maybe_str(payload, "topic_id", current.topic_id),
                discussion_id=_maybe_str(payload, "discussion_id", current.discussion_id),
                reason=_maybe_str(payload, "reason", current.reason),
                title=_maybe_str(payload, "title", current.title),
                body=_maybe_str(payload, "body", current.body),
                created_by_agent_id=_maybe_int(payload, "created_by_agent_id", current.created_by_agent_id),
                source_turn_ids=_maybe_ids(payload, "source_turn_ids", current.source_turn_ids),
                metadata=_maybe_mapping(payload, "metadata", current.metadata),
                updated_at=utc_now(),
            )
            self._service.bundle.summaries.update(updated)
            return {"status": "updated", "item": _serialize_summary(updated)}

        if object_type == "turn":
            current = _require_turn(self._service, item_id)
            updated = replace(
                current,
                topic_id=_maybe_str(payload, "topic_id", current.topic_id),
                discussion_id=_maybe_str(payload, "discussion_id", current.discussion_id),
                participant_id=_maybe_str(payload, "participant_id", current.participant_id),
                speaker_agent_id=_maybe_int(payload, "speaker_agent_id", current.speaker_agent_id),
                selected_model_id=_maybe_int(payload, "selected_model_id", current.selected_model_id),
                turn_index=_maybe_int(payload, "turn_index", current.turn_index) or 0,
                turn_kind=_maybe_str(payload, "turn_kind", current.turn_kind),
                content=_maybe_str(payload, "content", current.content),
                tool_name=_maybe_optional_text(payload, "tool_name", current.tool_name),
                tool_status=_maybe_optional_text(payload, "tool_status", current.tool_status),
                metadata=_maybe_mapping(payload, "metadata", current.metadata),
                updated_at=utc_now(),
            )
            self._service.bundle.turns.update(updated)
            return {"status": "updated", "item": _serialize_turn(updated)}

        raise ValueError(f"Unsupported topic management object type: {object_type}")

    def _delete_object(
        self,
        object_type: str,
        *,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any]:
        item_id = _required_text(payload.get("item_id"), field_name="item_id")
        if object_type == "topic":
            deleted = self._service.bundle.topics.delete(item_id)
        elif object_type == "discussion":
            deleted = self._service.bundle.discussions.delete(item_id)
        elif object_type == "participant":
            deleted = self._service.bundle.participants.delete(item_id)
        elif object_type == "summary":
            deleted = self._service.bundle.summaries.delete(item_id)
        elif object_type == "turn":
            deleted = self._service.bundle.turns.delete(item_id)
        else:
            raise ValueError(f"Unsupported topic management object type: {object_type}")
        return {"status": "deleted" if deleted else "not_found", "item_id": item_id, "deleted": bool(deleted)}

    def _assess_transition(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        result = self._service.detect_topic_transition(
            prompt=str(payload.get("prompt") or ""),
            topic_id=payload.get("topic_id"),
            explicit_action=_maybe_optional_text(payload, "explicit_action", None),
            moved_discussion=bool(payload.get("moved_discussion", False)),
        )
        return {
            "decision": result.decision,
            "source": result.source,
            "confidence": result.confidence,
            "reason": result.reason,
            "suggested_topic_title": result.suggested_topic_title,
        }

    def _summarize_topic(self, payload: Mapping[str, Any], *, context: ModuleViewContext) -> dict[str, Any]:
        topic_id = _required_text(payload.get("topic_id"), field_name="topic_id")
        discussion_id = _maybe_optional_text(payload, "discussion_id")
        if not _summary_has_participants(self._service, topic_id=topic_id, discussion_id=discussion_id):
            raise ValueError("Select participants before creating a topic summary.")
        summary = replace(
            self._service.draft_topic_summary(
                topic_id=topic_id,
                reason=str(payload.get("reason") or "maintenance"),
                discussion_id=discussion_id,
                created_by_agent_id=_maybe_int(payload, "created_by_agent_id", None),
                max_turns=_maybe_int(payload, "max_turns", 8) or 8,
            ),
            owner_user_id=context.user_id,
            owner_group_id=next(iter(context.group_ids), None),
        )
        self._service.bundle.summaries.update(summary)
        return {"status": "created", "item": _serialize_summary(summary)}


def _view_from_command(command: CommandContribution) -> ViewContribution:
    view_id = str(command.metadata.get("collection_view_id") or "").strip()
    return ViewContribution(
        module_id=command.module_id,
        action_id=command.action_id,
        view_id=view_id,
        name=command.name,
        description=command.description,
        metadata=dict(command.metadata or {}),
    )


def _object_type(metadata: Mapping[str, Any]) -> str:
    object_type = str(metadata.get("object_type") or "").strip()
    if not object_type:
        raise ValueError("Module metadata is missing object_type.")
    return object_type


def _command_verb(command_id: str) -> str:
    parts = [part for part in str(command_id).split(".") if part]
    return "" if not parts else parts[-1].lower()


def _parse_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _parse_tags(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _parse_ids(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _required_text(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    return text


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    return float(value)


def _maybe_str(payload: Mapping[str, Any], key: str, current: Any) -> Any:
    if key not in payload:
        return current
    raw = payload.get(key)
    if raw is None:
        return None
    return str(raw).strip()


def _maybe_optional_text(payload: Mapping[str, Any], key: str, current: Any = None) -> Any:
    if key not in payload:
        return current
    return _optional_text(payload.get(key))


def _maybe_int(payload: Mapping[str, Any], key: str, current: Any = None) -> Any:
    if key not in payload:
        return current
    raw = payload.get(key)
    return None if raw in (None, "") else int(raw)


def _maybe_float(payload: Mapping[str, Any], key: str, current: Any = None) -> Any:
    if key not in payload:
        return current
    return _optional_float(payload.get(key), default=current)


def _maybe_tags(payload: Mapping[str, Any], key: str, current: Any) -> Any:
    if key not in payload:
        return current
    return _parse_tags(payload.get(key))


def _maybe_ids(payload: Mapping[str, Any], key: str, current: Any) -> Any:
    if key not in payload:
        return current
    return _parse_ids(payload.get(key))


def _maybe_mapping(payload: Mapping[str, Any], key: str, current: Any) -> Any:
    if key not in payload:
        return current
    return _parse_mapping(payload.get(key))


def _maybe_dt(payload: Mapping[str, Any], key: str, current: Any) -> Any:
    if key not in payload:
        return current
    raw = payload.get(key)
    if raw in (None, ""):
        return None
    if isinstance(raw, datetime):
        return raw
    return datetime.fromisoformat(str(raw))


def _serialize_topic(topic: Topic) -> dict[str, Any]:
    return {
        "id": topic.id,
        "owner_user_id": topic.owner_user_id,
        "owner_group_id": topic.owner_group_id,
        "mode": topic.mode,
        "created_at": topic.created_at.isoformat(),
        "updated_at": topic.updated_at.isoformat(),
        "title": topic.title,
        "description": topic.description,
        "status": topic.status,
        "owner_agent_id": topic.owner_agent_id,
        "parent_topic_id": topic.parent_topic_id,
        "summary_id": topic.summary_id,
        "tags": list(topic.tags),
        "metadata": dict(topic.metadata),
    }


def _serialize_discussion(discussion: Discussion, *, service: Any | None = None) -> dict[str, Any]:
    return {
        "id": discussion.id,
        "owner_user_id": discussion.owner_user_id,
        "owner_group_id": discussion.owner_group_id,
        "mode": discussion.mode,
        "created_at": discussion.created_at.isoformat(),
        "updated_at": discussion.updated_at.isoformat(),
        "topic_id": discussion.topic_id,
        "title": discussion.title,
        "status": discussion.status,
        "summary_id": discussion.summary_id,
        "started_at": None if discussion.started_at is None else discussion.started_at.isoformat(),
        "last_activity_at": None if discussion.last_activity_at is None else discussion.last_activity_at.isoformat(),
        "closed_at": None if discussion.closed_at is None else discussion.closed_at.isoformat(),
        "participant_count": _discussion_participant_count(service, discussion) if service is not None else None,
        "topic_title": _discussion_topic_title(service, discussion) if service is not None else None,
        "chat_preview": _discussion_chat_preview(service, discussion) if service is not None else None,
        "metadata": dict(discussion.metadata),
    }


def _serialize_participant(participant: DiscussionParticipant) -> dict[str, Any]:
    participant_type = "group" if participant.group_id is not None else "agent" if participant.agent_id is not None else "unassigned"
    return {
        "id": participant.id,
        "owner_user_id": participant.owner_user_id,
        "owner_group_id": participant.owner_group_id,
        "mode": participant.mode,
        "created_at": participant.created_at.isoformat(),
        "updated_at": participant.updated_at.isoformat(),
        "discussion_id": participant.discussion_id,
        "agent_id": participant.agent_id,
        "group_id": participant.group_id,
        "type": participant_type,
        "title": _participant_name(None, participant),
        "role": participant.role,
        "selected_model_id": participant.selected_model_id,
        "turn_policy": participant.turn_policy,
        "temperature_override": participant.temperature_override,
        "tool_restrictions": list(participant.tool_restrictions),
        "metadata": dict(participant.metadata),
    }


def _serialize_summary(summary: TopicSummary) -> dict[str, Any]:
    return {
        "id": summary.id,
        "owner_user_id": summary.owner_user_id,
        "owner_group_id": summary.owner_group_id,
        "mode": summary.mode,
        "created_at": summary.created_at.isoformat(),
        "updated_at": summary.updated_at.isoformat(),
        "topic_id": summary.topic_id,
        "discussion_id": summary.discussion_id,
        "reason": summary.reason,
        "title": summary.title,
        "body": summary.body,
        "created_by_agent_id": summary.created_by_agent_id,
        "source_turn_ids": list(summary.source_turn_ids),
        "metadata": dict(summary.metadata),
    }


def _serialize_turn(turn: DiscussionTurn, *, service: Any | None = None) -> dict[str, Any]:
    return {
        "id": turn.id,
        "owner_user_id": turn.owner_user_id,
        "owner_group_id": turn.owner_group_id,
        "mode": turn.mode,
        "created_at": turn.created_at.isoformat(),
        "updated_at": turn.updated_at.isoformat(),
        "topic_id": turn.topic_id,
        "discussion_id": turn.discussion_id,
        "participant_id": turn.participant_id,
        "speaker_agent_id": turn.speaker_agent_id,
        "speaker_name": _agent_name(service, turn.speaker_agent_id) if service is not None else None,
        "selected_model_id": turn.selected_model_id,
        "selected_model_name": _model_name(service, turn.selected_model_id) if service is not None else None,
        "turn_index": turn.turn_index,
        "turn_kind": turn.turn_kind,
        "content": turn.content,
        "tool_name": turn.tool_name,
        "tool_status": turn.tool_status,
        "metadata": dict(turn.metadata),
    }


def _is_visible(item: Any, *, context: ModuleViewContext) -> bool:
    if context.user_id is not None and getattr(item, "owner_user_id", None) == context.user_id:
        return True
    owner_group_id = getattr(item, "owner_group_id", None)
    if owner_group_id is not None and owner_group_id in context.group_ids:
        return True
    return context.user_id is None and not context.group_ids


def _topic_sort_key(topic: Topic) -> Any:
    return (topic.updated_at, topic.created_at, topic.title.lower(), str(topic.id))


def _discussion_sort_key(discussion: Discussion) -> Any:
    return (discussion.last_activity_at or discussion.updated_at, discussion.created_at, discussion.title.lower(), str(discussion.id))


def _participant_sort_key(participant: DiscussionParticipant) -> Any:
    return (participant.updated_at, participant.created_at, participant.discussion_id or "", participant.agent_id or -1, str(participant.id))


def _summary_sort_key(summary: TopicSummary) -> Any:
    return (summary.created_at, summary.updated_at, summary.title.lower(), str(summary.id))


def _turn_sort_key(turn: DiscussionTurn) -> Any:
    return (turn.turn_index, turn.created_at, turn.updated_at, str(turn.id))


def _build_recent_chat_roster(service: TopicManagementService, *, context: ModuleViewContext) -> list[dict[str, Any]]:
    discussions = [discussion for discussion in service.list_discussions() if _is_visible(discussion, context=context)]
    discussions.sort(key=_discussion_sort_key, reverse=True)
    roster: list[dict[str, Any]] = []
    seen_agent_keys: set[tuple[str, str, str | None]] = set()
    for discussion in discussions:
        discussion_id = str(discussion.id or "")
        if not discussion_id:
            continue
        participants = [
            participant
            for participant in service.list_participants(discussion_id=discussion_id)
            if _is_visible(participant, context=context)
        ]
        if not participants:
            continue

        topic = service.bundle.topics.get(discussion.topic_id) if discussion.topic_id is not None else None
        latest_turn = _latest_turn_for_discussion(service, discussion_id)
        roster_item = {
            "id": f"discussion:{discussion_id}",
            "type": "group_chat" if len(participants) > 1 or discussion.owner_group_id is not None else "direct_chat",
            "discussion_id": discussion_id,
            "title": discussion.title or (topic.title if topic is not None else "Untitled Discussion"),
            "topic_id": discussion.topic_id,
            "topic_title": None if topic is None else topic.title,
            "last_activity_at": None if discussion.last_activity_at is None else discussion.last_activity_at.isoformat(),
            "participant_count": len(participants),
            "agent_ids": [participant.agent_id for participant in participants if participant.agent_id is not None],
            "selected_model_ids": [participant.selected_model_id for participant in participants if participant.selected_model_id is not None],
            "chat_preview": None if latest_turn is None else latest_turn.content,
            "status": discussion.status,
        }
        roster.append(roster_item)

        for participant in participants:
            participant_type = "group" if participant.group_id is not None else "agent"
            identifier = str(participant.group_id if participant.group_id is not None else participant.agent_id or "")
            if not identifier:
                continue
            key = (
                participant_type,
                identifier,
                discussion.topic_id if discussion.topic_id is None else str(discussion.topic_id),
            )
            if key in seen_agent_keys:
                continue
            participant_name = _participant_name(service, participant)
            model_name = _model_name(service, participant.selected_model_id)
            roster.append(
                {
                    "id": f"{participant_type}:{identifier}:{discussion_id}",
                    "type": participant_type,
                    "discussion_id": discussion_id,
                    "title": participant_name,
                    "topic_id": discussion.topic_id,
                    "topic_title": None if topic is None else topic.title,
                    "last_activity_at": None if discussion.last_activity_at is None else discussion.last_activity_at.isoformat(),
                    "participant_count": 1,
                    "agent_id": participant.agent_id,
                    "group_id": participant.group_id,
                    "selected_model_id": participant.selected_model_id,
                    "selected_model_name": model_name,
                    "chat_preview": None if latest_turn is None else latest_turn.content,
                    "status": discussion.status,
                }
            )
            seen_agent_keys.add(key)

    standalone_participants = [
        participant
        for participant in service.list_participants()
        if participant.discussion_id is None and _is_visible(participant, context=context)
    ]
    standalone_participants.sort(key=_participant_sort_key, reverse=True)
    for participant in standalone_participants:
        participant_type = "group" if participant.group_id is not None else "agent"
        identifier = str(participant.group_id if participant.group_id is not None else participant.agent_id or "")
        if not identifier:
            continue
        key = (participant_type, identifier, None)
        if key in seen_agent_keys:
            continue
        roster.append(
            {
                "id": f"{participant_type}:{identifier}",
                "type": participant_type,
                "discussion_id": None,
                "title": _participant_name(service, participant),
                "topic_id": None,
                "topic_title": None,
                "last_activity_at": participant.created_at.isoformat(),
                "participant_count": 1,
                "agent_id": participant.agent_id,
                "group_id": participant.group_id,
                "selected_model_id": participant.selected_model_id,
                "selected_model_name": _model_name(service, participant.selected_model_id),
                "chat_preview": "Ready to start a conversation.",
                "status": "active",
            }
        )
        seen_agent_keys.add(key)

    roster.sort(
        key=lambda item: (
            item.get("last_activity_at") or "",
            item.get("discussion_id") or "",
            item.get("type") or "",
            item.get("title") or "",
        ),
        reverse=True,
    )
    return roster


def _latest_turn_for_discussion(service: TopicManagementService, discussion_id: str) -> DiscussionTurn | None:
    turns = service.list_turns(discussion_id=discussion_id)
    if not turns:
        return None
    return turns[-1]


def _discussion_participant_count(service: Any | None, discussion: Discussion) -> int | None:
    if service is None or discussion.id is None:
        return None
    return len(service.list_participants(discussion_id=str(discussion.id)))


def _discussion_topic_title(service: Any | None, discussion: Discussion) -> str | None:
    if service is None or discussion.topic_id is None:
        return None
    topic = service.bundle.topics.get(discussion.topic_id)
    return None if topic is None else topic.title or None


def _discussion_chat_preview(service: Any | None, discussion: Discussion) -> str | None:
    if service is None or discussion.id is None:
        return None
    latest_turn = _latest_turn_for_discussion(service, str(discussion.id))
    return None if latest_turn is None else latest_turn.content


def _agent_name(service: Any | None, agent_id: int | None) -> str | None:
    if agent_id is None:
        return None
    return f"Agent {agent_id}"


def _participant_name(service: Any | None, participant: DiscussionParticipant) -> str:
    if participant.group_id is not None:
        return f"Group {participant.group_id}"
    if participant.agent_id is not None:
        return _agent_name(service, participant.agent_id) or "Unassigned participant"
    return "Unassigned participant"


def _model_name(service: Any | None, model_id: int | None) -> str | None:
    if model_id is None:
        return None
    try:
        config = LLMManager().get_config(int(model_id))
    except Exception:
        config = None
    if config is not None:
        alias = str(getattr(config, "user_alias", "") or "").strip()
        if alias:
            return alias
        provider = str(getattr(config, "provider_name", "") or "").strip()
        if provider:
            return provider
    return f"Model {model_id}"


def _parse_participant_target(payload: Mapping[str, Any]) -> tuple[str, str | int]:
    raw_target = _optional_text(payload.get("chat_target")) or _optional_text(payload.get("target"))
    if raw_target:
        prefix, _, value = raw_target.partition(":")
        prefix = prefix.strip().lower()
        value = value.split(" - ", 1)[0].strip()
        if prefix in {"agent", "group"} and value:
            return prefix, value

    if payload.get("group_id") not in (None, ""):
        return "group", str(payload.get("group_id")).strip()

    if payload.get("agent_id") not in (None, ""):
        return "agent", payload.get("agent_id")

    raise ValueError("Choose an agent or group for the participant.")


def _maybe_text(payload: Mapping[str, Any], key: str, current: Any = None) -> Any:
    if key not in payload:
        return current
    return _optional_text(payload.get(key))


def _summary_has_participants(
    service: TopicManagementService,
    *,
    topic_id: str | None,
    discussion_id: str | None,
) -> bool:
    if discussion_id is not None and service.list_participants(discussion_id=discussion_id):
        return True
    if topic_id is None:
        return False
    for discussion in service.list_discussions(topic_id=topic_id):
        if discussion.id is not None and service.list_participants(discussion_id=str(discussion.id)):
            return True
    return False


def _require_topic(service: TopicManagementService, item_id: str) -> Topic:
    topic = service.bundle.topics.get(item_id)
    if topic is None:
        raise ValueError(f"Topic not found: {item_id}")
    return topic


def _require_discussion(service: TopicManagementService, item_id: str) -> Discussion:
    discussion = service.bundle.discussions.get(item_id)
    if discussion is None:
        raise ValueError(f"Discussion not found: {item_id}")
    return discussion


def _require_participant(service: TopicManagementService, item_id: str) -> DiscussionParticipant:
    participant = service.bundle.participants.get(item_id)
    if participant is None:
        raise ValueError(f"Participant not found: {item_id}")
    return participant


def _require_summary(service: TopicManagementService, item_id: str) -> TopicSummary:
    summary = service.bundle.summaries.get(item_id)
    if summary is None:
        raise ValueError(f"Summary not found: {item_id}")
    return summary


def _require_turn(service: TopicManagementService, item_id: str) -> DiscussionTurn:
    turn = service.bundle.turns.get(item_id)
    if turn is None:
        raise ValueError(f"Turn not found: {item_id}")
    return turn
