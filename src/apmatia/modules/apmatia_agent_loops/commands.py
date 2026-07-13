from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS = [
    CommandContribution(
        module_id="apmatia_agent_loops",
        action_id="apmatia_agent_loops.tasks",
        command_id="apmatia_agent_loops.tasks.stop",
        name="Stop task",
        description="Request cancellation for a running loop task.",
        metadata={"verb": "stop", "object_type": "task"},
    )
]
