from __future__ import annotations

from unittest.mock import patch

from apmatia.core.module_view_runtime import (
    execute_module_command,
    list_module_view_items,
    register_module_view_provider,
)
from apmatia.core.registry import CommandContribution, ModuleMetadata, Registry, ViewContribution


class _StubProvider:
    def __init__(self) -> None:
        self.commands: list[tuple[str, dict, int | None, frozenset[int]]] = []

    def list_items(self, *, view, context):
        return [{"view_id": view.view_id, "user_id": context.user_id}]

    def execute_command(self, *, command, payload, context):
        self.commands.append((command.command_id, dict(payload), context.user_id, context.group_ids))
        return {"status": "ok", "command_id": command.command_id}


def _registry() -> Registry:
    registry = Registry()
    registry.register_module(ModuleMetadata(module_id="example", name="Example"))
    registry.register_view(
        ViewContribution(
            module_id="example",
            action_id="example.items",
            view_id="example.items.view",
            name="Items",
            metadata={"object_type": "item"},
        )
    )
    registry.register_command(
        CommandContribution(
            module_id="example",
            command_id="example.items.create",
            name="Create item",
            metadata={"object_type": "item", "verb": "create"},
        )
    )
    return registry


def test_module_view_runtime_dispatches_to_registered_provider():
    provider = _StubProvider()
    register_module_view_provider("example", provider)

    with patch("apmatia.core.module_view_runtime.get_application_registry", return_value=_registry()):
        items = list_module_view_items("example.items.view", user_id=7, group_ids={3})
        result = execute_module_command(
            "example.items.create",
            payload={"title": "Alpha"},
            user_id=7,
            group_ids={3},
        )

    assert items == [{"view_id": "example.items.view", "user_id": 7}]
    assert result == {"status": "ok", "command_id": "example.items.create"}
    assert provider.commands == [("example.items.create", {"title": "Alpha"}, 7, frozenset({3}))]
