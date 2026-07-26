from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS = [
    CommandContribution(
        module_id="agent_loops",
        command_id="agent_loops.stop",
        path=("agent_loops", "stop"),
        name="Stop task",
        description="Request cancellation for a running loop task.",
        metadata={"verb": "stop", "object_type": "task"},
    )
]
