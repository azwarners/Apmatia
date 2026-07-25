from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = tuple(
    CommandContribution(
        module_id="agent_tools",
        action_id="agent_tools.agent_tools",
        command_id=f"agent_tools.agent_tools.{verb}",
        path=("agent_tools", verb),
        name=f"Agent Tools {verb.title()}",
        description=f"{verb.title()} an agent tool definition.",
        metadata={
            "object_type": "agent_tool",
            "verb": verb,
            "collection_view_id": "agent_tools.agent_tools.view",
        },
    )
    for verb in ("list", "create", "edit")
)
