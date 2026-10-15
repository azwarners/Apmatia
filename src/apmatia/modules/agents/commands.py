from __future__ import annotations

from apmatia.core.registry import CommandContribution


_VERBS = ("list", "create", "edit", "clone", "delete", "install_starters")


def _input_fields(verb: str) -> list[dict[str, object]]:
    fields: list[dict[str, object]] = []
    if verb in {"edit", "clone", "delete"}:
        fields.append({"key": "item_id", "label": "Agent ID", "data_type": "number", "required": True})
    if verb in {"create", "edit"}:
        fields.extend(
            [
                {"key": "name", "label": "Name", "required": verb == "create"},
                {"key": "prompt_id", "label": "Prompt ID", "data_type": "number"},
                {"key": "default_model_id", "label": "Default Model ID", "data_type": "number"},
                {"key": "active_model_id", "label": "Active Model ID", "data_type": "number"},
                {"key": "workspace_root", "label": "Workspace Root"},
                {"key": "knowledge_root", "label": "Knowledge Root"},
            ]
        )
    if verb == "install_starters":
        fields.extend(
            [
                {"key": "default_model_id", "label": "Default Model ID", "data_type": "number"},
                {
                    "key": "publish",
                    "label": "Publish new profiles publicly",
                    "data_type": "boolean",
                    "default": False,
                    "help_text": "Explicitly publish newly installed prompt-only profiles. Existing agents are never changed.",
                },
            ]
        )
    return fields

COMMAND_DESCRIPTORS: tuple[CommandContribution, ...] = tuple(
    CommandContribution(
        module_id="agents",
        command_id=f"agents.{verb}",
        path=("agents", verb),
        name=f"Agents {verb.title()}",
        description=(
            "Install the bundled starter profiles without overwriting existing agents."
            if verb == "install_starters"
            else f"{verb.title()} agents through the stable agents module."
        ),
        metadata={
            "object_type": "agent",
            "verb": verb,
            "collection_view_id": "agents.agents.view",
            "input_fields": _input_fields(verb),
        },
    )
    for verb in _VERBS
)
