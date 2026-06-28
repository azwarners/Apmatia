from __future__ import annotations

from src.core.registry import ActionContribution, CommandContribution, ModuleMetadata, Registry, ViewContribution

EXAMPLE_MODULE = ModuleMetadata(
    module_id="example",
    name="Example Module",
    version="0.1.0",
    description="Minimal bundled example module.",
)

EXAMPLE_ACTION = ActionContribution(
    module_id=EXAMPLE_MODULE.module_id,
    action_id="example.action",
    name="Example Action",
    description="An example action descriptor.",
)

EXAMPLE_COMMAND = CommandContribution(
    module_id=EXAMPLE_MODULE.module_id,
    action_id=EXAMPLE_ACTION.action_id,
    command_id="example.command",
    name="Example Command",
    description="An example command descriptor.",
)

EXAMPLE_VIEW = ViewContribution(
    module_id=EXAMPLE_MODULE.module_id,
    action_id=EXAMPLE_ACTION.action_id,
    view_id="example.view",
    name="Example View",
    description="An example view descriptor.",
)


def register(registry: Registry) -> None:
    registry.register_module(EXAMPLE_MODULE)
    registry.register_action(EXAMPLE_ACTION)
    registry.register_command(EXAMPLE_COMMAND)
    registry.register_view(EXAMPLE_VIEW)
