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
)
