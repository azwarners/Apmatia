from __future__ import annotations

from typing import Any

from apmatia.core.view_contract import normalize_view_document

from .actions import ActionContribution
from .commands import CommandContribution
from .modules import ModuleMetadata
from .tools import ToolContribution
from .views import ViewContribution


class Registry:
    def __init__(self) -> None:
        self._modules: dict[str, ModuleMetadata] = {}
        self._actions: dict[str, ActionContribution] = {}
        self._tools: dict[str, ToolContribution] = {}
        self._commands: dict[str, CommandContribution] = {}
        self._views: dict[str, ViewContribution] = {}

    def register_module(self, module: ModuleMetadata | None = None, **kwargs: Any) -> ModuleMetadata:
        record = module or ModuleMetadata(**kwargs)
        self._validate_identifier(record.module_id, "module_id")
        self._modules[record.module_id] = record
        return record

    def register_action(self, action: ActionContribution | None = None, **kwargs: Any) -> ActionContribution:
        record = action or ActionContribution(**kwargs)
        self._validate_identifier(record.action_id, "action_id")
        self._validate_identifier(record.module_id, "module_id")
        self._actions[record.action_id] = record
        return record

    def register_tool(self, tool: ToolContribution | None = None, **kwargs: Any) -> ToolContribution:
        record = tool or ToolContribution(**kwargs)
        self._validate_identifier(record.tool_id, "tool_id")
        self._validate_identifier(record.action_id, "action_id")
        self._validate_identifier(record.module_id, "module_id")
        self._tools[record.tool_id] = record
        return record

    def register_command(self, command: CommandContribution | None = None, **kwargs: Any) -> CommandContribution:
        record = command or CommandContribution(**kwargs)
        self._validate_identifier(record.command_id, "command_id")
        self._validate_identifier(record.module_id, "module_id")
        self._commands[record.command_id] = record
        return record

    def register_view(self, view: ViewContribution | None = None, **kwargs: Any) -> ViewContribution:
        record = view or ViewContribution(**kwargs)
        self._validate_identifier(record.view_id, "view_id")
        self._validate_identifier(record.action_id, "action_id")
        self._validate_identifier(record.module_id, "module_id")
        # Validate the portable compatibility document at registration time so malformed view
        # metadata fails once, before individual renderers interpret it differently.
        normalize_view_document(record)
        self._views[record.view_id] = record
        return record

    def list_modules(self, *, include_development: bool = False) -> list[ModuleMetadata]:
        modules = [self._modules[module_id] for module_id in sorted(self._modules)]
        if include_development:
            return modules
        return [module for module in modules if module.is_visible_by_default]

    def list_actions(self) -> list[ActionContribution]:
        return [self._actions[action_id] for action_id in sorted(self._actions)]

    def list_tools(self) -> list[ToolContribution]:
        return [self._tools[tool_id] for tool_id in sorted(self._tools)]

    def list_commands(self) -> list[CommandContribution]:
        return [self._commands[command_id] for command_id in sorted(self._commands)]

    def list_views(self) -> list[ViewContribution]:
        return [self._views[view_id] for view_id in sorted(self._views)]

    @staticmethod
    def _validate_identifier(value: str, field_name: str) -> None:
        if value is None or not str(value).strip():
            raise ValueError(f"{field_name} cannot be empty.")
