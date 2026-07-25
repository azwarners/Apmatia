from __future__ import annotations

from apmatia.core.registry import CommandContribution


_VERBS = ("list", "create", "edit", "delete")

COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = tuple(
    CommandContribution(
        module_id="agents",
        action_id="agents.agents",
        command_id=f"agents.agents.{verb}",
        path=("agents", verb),
        name=f"Agents {verb.title()}",
        description=f"{verb.title()} agents through the stable agents module.",
        metadata={
            "object_type": "agent",
            "verb": verb,
            "collection_view_id": "agents.agents.view",
        },
    )
    for verb in _VERBS
)
