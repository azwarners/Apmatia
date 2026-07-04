from __future__ import annotations

from apmatia.core.registry import CommandContribution


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = (
    CommandContribution(
        module_id="apmatia_ai_model_executor",
        action_id="apmatia_ai_model_executor.resources",
        command_id="apmatia_ai_model_executor.resources.inspect",
        path=("apmatia_ai_model_executor", "resources", "inspect"),
        name="Inspect Host Resources",
        description="Inspect host RAM and VRAM resources as JSON.",
        metadata={"object_type": "host_resources", "verb": "resources"},
    ),
    CommandContribution(
        module_id="apmatia_ai_model_executor",
        action_id="apmatia_ai_model_executor.executions",
        command_id="apmatia_ai_model_executor.executions.can_run",
        path=("apmatia_ai_model_executor", "executions", "can_run"),
        name="Can Run Model",
        description="Check whether a model can run on the current host.",
        metadata={"object_type": "model_execution", "verb": "can-run"},
    ),
    CommandContribution(
        module_id="apmatia_ai_model_executor",
        action_id="apmatia_ai_model_executor.executions",
        command_id="apmatia_ai_model_executor.executions.start",
        path=("apmatia_ai_model_executor", "executions", "start"),
        name="Start Model",
        description="Start a local llama.cpp execution for a model.",
        metadata={"object_type": "model_execution", "verb": "start"},
    ),
    CommandContribution(
        module_id="apmatia_ai_model_executor",
        action_id="apmatia_ai_model_executor.executions",
        command_id="apmatia_ai_model_executor.executions.stop",
        path=("apmatia_ai_model_executor", "executions", "stop"),
        name="Stop Model",
        description="Stop a running local model execution.",
        metadata={"object_type": "model_execution", "verb": "stop"},
    ),
    CommandContribution(
        module_id="apmatia_ai_model_executor",
        action_id="apmatia_ai_model_executor.executions",
        command_id="apmatia_ai_model_executor.executions.status",
        path=("apmatia_ai_model_executor", "executions", "status"),
        name="Execution Status",
        description="Show execution status records.",
        metadata={"object_type": "model_execution", "verb": "status"},
    ),
)
