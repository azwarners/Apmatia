from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS = [
    CommandContribution(
        module_id="agent_loops",
        command_id="agent_loops.start",
        path=("agent_loops", "start"),
        name="Start task",
        description="Start a contact-owned agent loop task.",
        metadata={
            "verb": "start",
            "object_type": "task",
            "input_fields": [
                {"key": "contact_id", "label": "Contact ID", "field_type": "text", "required": True},
                {"key": "title", "label": "Task title", "field_type": "text", "required": True},
                {"key": "prompt", "label": "Prompt", "field_type": "textarea", "required": True},
                {"key": "max_iterations", "label": "Max turns", "field_type": "number", "default": 10},
            ],
        },
    ),
    CommandContribution(
        module_id="agent_loops",
        command_id="agent_loops.stop",
        path=("agent_loops", "stop"),
        name="Stop task",
        description="Request cancellation for a running loop task.",
        metadata={"verb": "stop", "object_type": "task"},
    )
]
