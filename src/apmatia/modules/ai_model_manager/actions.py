from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="ai_model_manager",
        action_id="ai_model_manager.models",
        name="GGUF Model Management",
        description="Inspect and maintain local GGUF model records.",
        metadata={"object_type": "gguf_model"},
    ),
    ActionContribution(
        module_id="ai_model_manager",
        action_id="ai_model_manager.preferences",
        name="Task Model Preferences",
        description="Store routing preferences for tasks and model sizes.",
        metadata={"object_type": "task_preference"},
    ),
    ActionContribution(
        module_id="ai_model_manager",
        action_id="ai_model_manager.llm_configs",
        name="Remote LLM Configurations",
        description="Manage remote LLM endpoint configurations.",
        metadata={"object_type": "llm_config"},
    ),
)

