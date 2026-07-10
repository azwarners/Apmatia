from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = (
    CommandContribution(
        module_id="apmatia_agent_loops",
        action_id="apmatia_agent_loops.tasks",
        command_id="apmatia_agent_loops.tasks.stop",
        path=("apmatia_agent_loops", "tasks", "stop"),
        name="Stop Task",
        description="Stop a running agent loop task.",
        metadata={"object_type": "run", "verb": "stop"},
    ),
)
