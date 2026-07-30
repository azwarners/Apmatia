from __future__ import annotations

from .actions import ACTION_DESCRIPTORS
from .collections import TOPIC_COLLECTION_VIEW_SPECS
from .commands import COMMAND_DESCRIPTORS
from .models import (
    DISCUSSION_STATUSES,
    PARTICIPANT_ROLES,
    PARTICIPANT_TURN_POLICIES,
    SUMMARY_REASONS,
    TOPIC_STATUSES,
    Topic,
    TopicSummary,
    Discussion,
    DiscussionParticipant,
    DiscussionTurn,
    TopicTransitionDecision,
)
from .module import APMATIA_DISCUSS_MODULE, APMATIA_TOPIC_MANAGEMENT_MODULE, register
from .module_views import ApmatiaTopicManagementModuleViewProvider
from .services import TopicManagementService, TopicTransitionDetector
from .sqlite_repositories import (
    TopicManagementBundle,
    TopicManagementTables,
    SQLiteDiscussionParticipantRepository,
    SQLiteDiscussionRepository,
    SQLiteDiscussionTurnRepository,
    SQLiteTopicRepository,
    SQLiteTopicSummaryRepository,
)
from .views import VIEW_DESCRIPTORS

__all__ = [
    "ACTION_DESCRIPTORS",
    "APMATIA_DISCUSS_MODULE",
    "APMATIA_TOPIC_MANAGEMENT_MODULE",
    "COMMAND_DESCRIPTORS",
    "DISCUSSION_STATUSES",
    "Discussion",
    "DiscussionParticipant",
    "DiscussionTurn",
    "PARTICIPANT_ROLES",
    "PARTICIPANT_TURN_POLICIES",
    "SQLiteDiscussionParticipantRepository",
    "SQLiteDiscussionRepository",
    "SQLiteDiscussionTurnRepository",
    "SQLiteTopicRepository",
    "SQLiteTopicSummaryRepository",
    "SUMMARY_REASONS",
    "TOPIC_COLLECTION_VIEW_SPECS",
    "TOPIC_STATUSES",
    "Topic",
    "TopicManagementBundle",
    "TopicManagementService",
    "TopicManagementTables",
    "TopicSummary",
    "TopicTransitionDetector",
    "TopicTransitionDecision",
    "VIEW_DESCRIPTORS",
    "ApmatiaTopicManagementModuleViewProvider",
    "register",
]
