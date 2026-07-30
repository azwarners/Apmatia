from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apmatia.core.module_view_schema import build_collection_view_schema

from .models import Discussion, DiscussionParticipant, DiscussionTurn, Topic, TopicSummary


@dataclass(frozen=True, slots=True)
class TopicCollectionViewSpec:
    action_id: str
    view_id: str
    object_type: str
    singular_label: str
    plural_label: str
    description: str
    schema: dict[str, Any]
    list_command_id: str
    create_command_id: str
    edit_command_id: str
    delete_command_id: str
    extra_command_ids: tuple[str, ...] = ()
    columns: tuple[dict[str, Any], ...] = ()


TOPIC_VIEW_SPEC = TopicCollectionViewSpec(
    action_id="discuss.topics",
    view_id="discuss.topics.view",
    object_type="topic",
    singular_label="Topic",
    plural_label="Topics",
    description="Organize work by subject and keep topic-level summaries alongside the active discussion.",
    schema=build_collection_view_schema(
        Topic,
        list_fields=("title", "status", "owner_agent_id", "summary_id", "tags"),
        create_fields=("title", "description", "owner_agent_id", "tags"),
        edit_fields=("title", "description", "status", "owner_agent_id", "parent_topic_id", "summary_id", "tags", "metadata"),
        field_overrides={
            "id": {"hidden": True},
            "owner_user_id": {"hidden": True},
            "owner_group_id": {"hidden": True},
            "mode": {"hidden": True},
            "created_at": {"hidden": True},
            "updated_at": {"hidden": True},
            "title": {"placeholder": "AI models"},
            "description": {"field_type": "textarea", "help_text": "Describe the work or subject the topic represents."},
            "status": {"field_type": "select", "options": ["active", "evolving", "closed", "archived"], "default": "active"},
            "owner_agent_id": {"label": "Owner agent", "help_text": "Optional agent that currently owns the topic."},
            "parent_topic_id": {"label": "Parent topic", "help_text": "Optional parent topic for nested workspaces."},
            "summary_id": {"label": "Summary", "help_text": "Current summary artifact attached to this topic."},
            "tags": {"field_type": "text", "placeholder": "architecture, planning"},
            "metadata": {"field_type": "textarea", "help_text": "Additional serialized metadata.", "hidden": True},
        },
        create={
            "title": "Create topic",
            "description": "Start a new subject of work.",
            "submit_label": "Create topic",
        },
    ),
    list_command_id="discuss.topics.list",
    create_command_id="discuss.topics.create",
    edit_command_id="discuss.topics.edit",
    delete_command_id="discuss.topics.delete",
    extra_command_ids=("discuss.topics.assess_transition", "discuss.topics.summarize"),
)

DISCUSSION_VIEW_SPEC = TopicCollectionViewSpec(
    action_id="discuss.discussions",
    view_id="discuss.discussions.view",
    object_type="discussion",
    singular_label="Discussion",
    plural_label="Discussions",
    description="Track topic-bound discussions as first-class work artifacts.",
    schema=build_collection_view_schema(
        Discussion,
        list_fields=("topic_id", "title", "status", "summary_id", "last_activity_at"),
        create_fields=("topic_id", "title", "status", "started_at"),
        edit_fields=("topic_id", "title", "status", "summary_id", "started_at", "last_activity_at", "closed_at", "metadata"),
        field_overrides={
            "id": {"hidden": True},
            "owner_user_id": {"hidden": True},
            "owner_group_id": {"hidden": True},
            "mode": {"hidden": True},
            "created_at": {"hidden": True},
            "updated_at": {"hidden": True},
            "topic_id": {"label": "Topic", "help_text": "The topic this discussion belongs to."},
            "title": {"placeholder": "Architecture discussion"},
            "status": {"field_type": "select", "options": ["active", "paused", "closed", "archived"], "default": "active"},
            "summary_id": {"label": "Summary"},
            "started_at": {"label": "Started at"},
            "last_activity_at": {"label": "Last activity at"},
            "closed_at": {"label": "Closed at"},
            "metadata": {"hidden": True},
        },
        create={
            "title": "Create discussion",
            "description": "Open a topic-bound discussion.",
            "submit_label": "Create discussion",
        },
    ),
    columns=(
        {"key": "title", "label": "Discussion"},
        {"key": "topic_title", "label": "Topic"},
        {"key": "participant_count", "label": "People"},
        {"key": "last_activity_at", "label": "Last Activity"},
        {"key": "chat_preview", "label": "Preview"},
    ),
    list_command_id="discuss.discussions.list",
    create_command_id="discuss.discussions.create",
    edit_command_id="discuss.discussions.edit",
    delete_command_id="discuss.discussions.delete",
)

PARTICIPANT_VIEW_SPEC = TopicCollectionViewSpec(
    action_id="discuss.chat_targets",
    view_id="discuss.chat_targets.view",
    object_type="participant",
    singular_label="Chat Target",
    plural_label="Chat Targets",
    description="Track the agents and groups you chat with, along with their runtime settings.",
    schema=build_collection_view_schema(
        DiscussionParticipant,
        list_fields=("agent_id", "group_id", "role", "selected_model_id", "turn_policy", "temperature_override"),
        create_fields=("agent_id", "group_id", "role", "selected_model_id", "turn_policy", "temperature_override", "tool_restrictions"),
        edit_fields=("agent_id", "group_id", "role", "selected_model_id", "turn_policy", "temperature_override", "tool_restrictions", "metadata"),
        field_overrides={
            "id": {"hidden": True},
            "owner_user_id": {"hidden": True},
            "owner_group_id": {"hidden": True},
            "mode": {"hidden": True},
            "created_at": {"hidden": True},
            "updated_at": {"hidden": True},
            "agent_id": {"label": "Agent"},
            "group_id": {"label": "Group"},
            "role": {"field_type": "select", "options": ["agent", "coordinator", "reviewer", "observer"], "default": "agent"},
            "selected_model_id": {"label": "Model alias"},
            "turn_policy": {"field_type": "select", "options": ["manual", "auto", "round_robin", "coordinator_only"], "default": "round_robin"},
            "temperature_override": {"label": "Temperature override", "field_type": "number", "min_value": 0.0, "max_value": 2.0, "step": 0.1},
            "tool_restrictions": {"field_type": "text", "placeholder": "wiki.read, memory.write"},
            "metadata": {"hidden": True},
        },
        create={
            "title": "Add chat target",
            "description": "Pick an agent or group first, then tune how Apmatia should chat with it.",
            "submit_label": "Save target",
        },
    ),
    columns=(
        {"key": "title", "label": "Chat"},
        {"key": "type", "label": "Type"},
        {"key": "topic_title", "label": "Topic"},
        {"key": "last_activity_at", "label": "Last Activity"},
        {"key": "selected_model_name", "label": "Model"},
        {"key": "chat_preview", "label": "Preview"},
    ),
    list_command_id="discuss.chat_targets.list",
    create_command_id="discuss.chat_targets.create",
    edit_command_id="discuss.chat_targets.edit",
    delete_command_id="discuss.chat_targets.delete",
)

SUMMARY_VIEW_SPEC = TopicCollectionViewSpec(
    action_id="discuss.summaries",
    view_id="discuss.summaries.view",
    object_type="summary",
    singular_label="Topic Summary",
    plural_label="Topic Summaries",
    description="Store topic-level summaries for closeout, compaction, and evolution tracking.",
    schema=build_collection_view_schema(
        TopicSummary,
        list_fields=("topic_id", "discussion_id", "reason", "title", "created_by_agent_id"),
        create_fields=("topic_id", "discussion_id", "reason", "title", "body", "created_by_agent_id", "source_turn_ids"),
        edit_fields=("topic_id", "discussion_id", "reason", "title", "body", "created_by_agent_id", "source_turn_ids", "metadata"),
        field_overrides={
            "id": {"hidden": True},
            "owner_user_id": {"hidden": True},
            "owner_group_id": {"hidden": True},
            "mode": {"hidden": True},
            "created_at": {"hidden": True},
            "updated_at": {"hidden": True},
            "topic_id": {"label": "Topic"},
            "discussion_id": {"label": "Discussion"},
            "reason": {"field_type": "select", "options": ["topic_closed", "topic_evolved", "user_requested", "maintenance"], "default": "maintenance"},
            "title": {"placeholder": "Weekly architecture summary"},
            "body": {"field_type": "textarea", "help_text": "Summaries should describe the work completed inside the topic."},
            "created_by_agent_id": {"label": "Created by agent"},
            "source_turn_ids": {"label": "Source turns", "field_type": "text"},
            "metadata": {"hidden": True},
        },
        create={
            "title": "Create summary",
            "description": "Capture a topic summary when work closes or evolves.",
            "submit_label": "Save summary",
        },
    ),
    columns=(
        {"key": "title", "label": "Summary"},
        {"key": "topic_title", "label": "Topic"},
        {"key": "reason", "label": "Reason"},
        {"key": "created_by_agent_id", "label": "Agent"},
    ),
    list_command_id="discuss.summaries.list",
    create_command_id="discuss.summaries.create",
    edit_command_id="discuss.summaries.edit",
    delete_command_id="discuss.summaries.delete",
)

TURN_VIEW_SPEC = TopicCollectionViewSpec(
    action_id="discuss.turns",
    view_id="discuss.turns.view",
    object_type="turn",
    singular_label="Discussion Turn",
    plural_label="Discussion Turns",
    description="Keep a structured turn log for each discussion.",
    schema=build_collection_view_schema(
        DiscussionTurn,
        list_fields=("discussion_id", "turn_index", "speaker_agent_id", "selected_model_id", "turn_kind", "content"),
        create_fields=("topic_id", "discussion_id", "participant_id", "speaker_agent_id", "selected_model_id", "turn_index", "turn_kind", "content", "tool_name", "tool_status"),
        edit_fields=("topic_id", "discussion_id", "participant_id", "speaker_agent_id", "selected_model_id", "turn_index", "turn_kind", "content", "tool_name", "tool_status", "metadata"),
        field_overrides={
            "id": {"hidden": True},
            "owner_user_id": {"hidden": True},
            "owner_group_id": {"hidden": True},
            "mode": {"hidden": True},
            "created_at": {"hidden": True},
            "updated_at": {"hidden": True},
            "topic_id": {"label": "Topic"},
            "discussion_id": {"label": "Discussion"},
            "participant_id": {"label": "Participant"},
            "speaker_agent_id": {"label": "Speaker agent"},
            "selected_model_id": {"label": "Model alias"},
            "turn_index": {"label": "Turn index", "min_value": 0, "step": 1},
            "turn_kind": {"field_type": "select", "options": ["assistant", "user", "tool", "system"], "default": "assistant"},
            "content": {"field_type": "textarea", "help_text": "Turn content or transcript fragment."},
            "tool_name": {"label": "Tool name"},
            "tool_status": {"label": "Tool status"},
            "metadata": {"hidden": True},
        },
        create={
            "title": "Add turn",
            "description": "Record a turn in a topic discussion.",
            "submit_label": "Save turn",
        },
    ),
    columns=(
        {"key": "turn_index", "label": "#"},
        {"key": "speaker_name", "label": "Speaker"},
        {"key": "selected_model_name", "label": "Model"},
        {"key": "turn_kind", "label": "Kind"},
        {"key": "content", "label": "Content"},
    ),
    list_command_id="discuss.turns.list",
    create_command_id="discuss.turns.create",
    edit_command_id="discuss.turns.edit",
    delete_command_id="discuss.turns.delete",
)


TOPIC_COLLECTION_VIEW_SPECS: tuple[TopicCollectionViewSpec, ...] = (
    PARTICIPANT_VIEW_SPEC,
    DISCUSSION_VIEW_SPEC,
    TOPIC_VIEW_SPEC,
    SUMMARY_VIEW_SPEC,
    TURN_VIEW_SPEC,
)
