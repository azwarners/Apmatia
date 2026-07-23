from __future__ import annotations

from apmatia.core.registry import CommandContribution

from .collections import AI_MODEL_COLLECTION_VIEW_SPECS


def _command_descriptors() -> tuple[CommandContribution, ...]:
    descriptors: list[CommandContribution] = []
    for spec in AI_MODEL_COLLECTION_VIEW_SPECS:
        for verb, command_id, description in (
            ("list", spec.list_command_id, f"List all {spec.plural_label.lower()}."),
            ("create", spec.create_command_id, f"Create a new {spec.singular_label.lower()}."),
            ("edit", spec.edit_command_id, f"Edit an existing {spec.singular_label.lower()}."),
            ("delete", spec.delete_command_id, f"Delete an existing {spec.singular_label.lower()}."),
        ):
            descriptors.append(
                CommandContribution(
                    module_id="ai_model_manager",
                    action_id=spec.action_id,
                    command_id=command_id,
                    path=tuple(command_id.split(".")),
                    name=f"{spec.singular_label} {verb.title()}",
                    description=description,
                    metadata={
                        "object_type": spec.object_type,
                        "verb": verb,
                        "collection_view_id": spec.view_id,
                    },
                )
            )

    model_spec = AI_MODEL_COLLECTION_VIEW_SPECS[0]
    descriptors.extend(
        (
            CommandContribution(
                module_id="ai_model_manager",
                action_id=model_spec.action_id,
                command_id=model_spec.scan_command_id,
                path=tuple(model_spec.scan_command_id.split(".")),
                name="Scan GGUF Directory",
                description="Scan a directory tree for GGUF files and refresh model records.",
                metadata={"object_type": model_spec.object_type, "verb": "scan", "collection_view_id": model_spec.view_id},
            ),
            CommandContribution(
                module_id="ai_model_manager",
                action_id=model_spec.action_id,
                command_id=model_spec.show_command_id,
                path=tuple(model_spec.show_command_id.split(".")),
                name="Show Model Details",
                description="Show a detailed view of a single GGUF model record.",
                metadata={"object_type": model_spec.object_type, "verb": "show", "collection_view_id": model_spec.view_id},
            ),
        )
    )

    # Add test command for LLM configs
    llm_spec = AI_MODEL_COLLECTION_VIEW_SPECS[2]
    descriptors.append(
        CommandContribution(
            module_id="ai_model_manager",
            action_id=llm_spec.action_id,
            command_id="ai_model_manager.llm_configs.test",
            path=("ai_model_manager", "llm_configs", "test"),
            name="Test LLM Config",
            description="Test connectivity to an LLM endpoint.",
            metadata={"object_type": llm_spec.object_type, "verb": "test", "collection_view_id": llm_spec.view_id},
        )
    )
    return tuple(descriptors)


COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = _command_descriptors()
