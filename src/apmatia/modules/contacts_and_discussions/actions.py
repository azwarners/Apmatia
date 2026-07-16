from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="contacts_and_discussions",
        action_id="contacts_and_discussions.chat_targets",
        name="Chat Targets",
        description="Choose the agents and groups you want to chat with, and tune their behavior.",
        metadata={"object_type": "participant"},
    ),
    ActionContribution(
        module_id="contacts_and_discussions",
        action_id="contacts_and_discussions.discussions",
        name="Topic Discussions",
        description="Track the discussion artifacts that live under a topic.",
        metadata={"object_type": "discussion"},
    ),
    ActionContribution(
        module_id="contacts_and_discussions",
        action_id="contacts_and_discussions.topics",
        name="Topic Management",
        description="Organize work by topic and manage the topic-level summary lifecycle.",
        metadata={"object_type": "topic"},
    ),
    ActionContribution(
        module_id="contacts_and_discussions",
        action_id="contacts_and_discussions.summaries",
        name="Topic Summaries",
        description="Store summaries for topic closeout and compaction.",
        metadata={"object_type": "summary"},
    ),
    ActionContribution(
        module_id="contacts_and_discussions",
        action_id="contacts_and_discussions.turns",
        name="Discussion Turns",
        description="Keep a structured turn log for topic discussions.",
        metadata={"object_type": "turn"},
    ),
)
