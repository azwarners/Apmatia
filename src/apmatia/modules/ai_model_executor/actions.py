from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="ai_model_executor",
        action_id="ai_model_executor.resources",
        name="Host Resource Inspection",
        description="Inspect local RAM and VRAM resources for model execution planning.",
        metadata={"object_type": "host_resources"},
    ),
    ActionContribution(
        module_id="ai_model_executor",
        action_id="ai_model_executor.executions",
        name="Model Execution Control",
        description="Start, stop, and inspect local llama.cpp model executions.",
        metadata={"object_type": "model_execution"},
    ),
    ActionContribution(
        module_id="ai_model_executor",
        action_id="ai_model_executor.queue",
        name="Work Queue Management",
        description="Enqueue, dequeue, and inspect pending work items in the executor queue.",
        metadata={"object_type": "queue_item"},
    ),
    ActionContribution(
        module_id="ai_model_executor",
        action_id="ai_model_executor.reservations",
        name="Seat Reservations",
        description="Reserve and release seats on model runtimes for interactive users.",
        metadata={"object_type": "reservation"},
    ),
    ActionContribution(
        module_id="ai_model_executor",
        action_id="ai_model_executor.capacity",
        name="Runtime Capacity",
        description="View runtime capacity, active leases, and admission control state.",
        metadata={"object_type": "capacity"},
    ),
)
