"""Command descriptors for the Apmatia Worksim module."""

from __future__ import annotations

from apmatia.core.registry import CommandContribution

from .collections import ORG_CHART_VIEW_SPECS


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = tuple(
    CommandContribution(
        module_id="apmatia_worksim",
        action_id=spec.action_id,
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
    for spec in ORG_CHART_VIEW_SPECS
    for verb, command_id, description in (
        (
            "list",
            spec.list_command_id,
            f"List all {spec.plural_label.lower()}.",
        ),
        (
            "create",
            spec.create_command_id,
            f"Create a new {spec.singular_label.lower()}.",
        ),
        (
            "edit",
            spec.edit_command_id,
            f"Edit an existing {spec.singular_label.lower()}.",
        ),
        (
            "delete",
            spec.delete_command_id,
            f"Delete an existing {spec.singular_label.lower()}.",
        ),
    )
)
