from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from apmatia.lib.apmatia_core.models import utc_now


class ToolProvider(Protocol):
    provider_id: str

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        raise NotImplementedError


@dataclass(slots=True)
class FunctionTool:
    provider_id: str
    handler: Callable[..., Any]

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        return self.handler(**arguments)


class ToolRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ToolProvider] = {}

    def register(self, provider: ToolProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> ToolProvider | None:
        return self._providers.get(provider_id)

    def list_provider_ids(self) -> list[str]:
        return sorted(self._providers.keys())


def register_builtin_tools(registry: ToolRegistry, providers: list[ToolProvider] | None = None) -> None:
    registry.register(FunctionTool("builtin.echo", _echo))
    registry.register(FunctionTool("builtin.get_current_time", _get_current_time))
    for provider in providers or []:
        registry.register(provider)


def builtin_tool_definitions(extra_definitions: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    definitions = [
        {
            "name": "echo",
            "description": "Return the provided text without modification.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            "provider_id": "builtin.echo",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "library": "tool_management"},
        },
        {
            "name": "get_current_time",
            "description": "Return the current UTC timestamp.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "current_time": {"type": "string"},
                },
                "required": ["current_time"],
                "additionalProperties": False,
            },
            "provider_id": "builtin.get_current_time",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "library": "tool_management"},
        },
    ]
    if extra_definitions:
        definitions.extend(extra_definitions)
    return definitions


def _echo(text: str) -> dict[str, str]:
    return {"text": text}


def _get_current_time() -> dict[str, str]:
    return {"current_time": utc_now().isoformat()}
