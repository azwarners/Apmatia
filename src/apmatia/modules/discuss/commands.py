from __future__ import annotations

from apmatia.core.registry import CommandContribution

from .collections import TOPIC_COLLECTION_VIEW_SPECS


def _command_descriptors() -> tuple[CommandContribution, ...]:
    descriptors: list[CommandContribution] = []
    for spec in TOPIC_COLLECTION_VIEW_SPECS:
        for verb, command_id, description in (
            ("list", spec.list_command_id, f"List all {spec.plural_label.lower()}."),
            ("create", spec.create_command_id, f"Create a new {spec.singular_label.lower()}."),
            ("edit", spec.edit_command_id, f"Edit an existing {spec.singular_label.lower()}."),
            ("delete", spec.delete_command_id, f"Delete an existing {spec.singular_label.lower()}."),
        ):
            descriptors.append(
                CommandContribution(
                    module_id="discuss",
                    command_id=command_id,
                    path=tuple(command_id.split(".")),
                    name=f"{spec.singular_label} {verb.title()}",
                    description=description,
                    metadata={
                        "object_type": spec.object_type,
                        "verb": verb,
                        "collection_view_id": spec.view_id,
                    },
                )
            )

    topic_spec = TOPIC_COLLECTION_VIEW_SPECS[0]
    descriptors.extend(
        (
            CommandContribution(
                module_id="discuss",
                command_id="discuss.discussion.create",
                path=("discuss", "discussion", "create"),
                name="Create Discussion",
                description="Create and select a new discussion.",
                metadata={"verb": "create_rich", "object_type": "discussion"},
            ),
            CommandContribution(
                module_id="discuss",
                command_id="discuss.discussion.open",
                path=("discuss", "discussion", "open"),
                name="Open Discussion",
                description="Select an existing discussion.",
                metadata={"verb": "open_rich", "object_type": "discussion"},
            ),
            CommandContribution(
                module_id="discuss",
                command_id="discuss.topics.assess_transition",
                path=("discuss", "topics", "assess_transition"),
                name="Assess Topic Transition",
                description="Run layered topic transition detection and report the decision.",
                metadata={"object_type": topic_spec.object_type, "verb": "assess_transition"},
            ),
            CommandContribution(
                module_id="discuss",
                command_id="discuss.topics.summarize",
                path=("discuss", "topics", "summarize"),
                name="Summarize Topic",
                description="Draft a topic-level summary from the current discussion history.",
                metadata={"object_type": topic_spec.object_type, "verb": "summarize"},
            ),
        )
    )
    return tuple(descriptors)


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = _command_descriptors()
