from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.core.registry import CommandContribution, ViewContribution, get_application_registry


@dataclass(frozen=True, slots=True)
class ModuleViewContext:
    user_id: int | None = None
    group_ids: frozenset[int] = field(default_factory=frozenset)


class ModuleViewProvider(Protocol):
    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]: ...

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None: ...


_providers: dict[str, ModuleViewProvider] = {}


def register_module_view_provider(module_id: str, provider: ModuleViewProvider) -> None:
    normalized_module_id = str(module_id or "").strip()
    if not normalized_module_id:
        raise ValueError("Module ID cannot be empty.")
    _providers[normalized_module_id] = provider


def list_module_view_items(
    view_id: str,
    *,
    user_id: int | None = None,
    group_ids: set[int] | None = None,
) -> list[dict[str, Any]]:
    view = _require_view(view_id)
    provider = _require_provider(view.module_id)
    return list(provider.list_items(view=view, context=_context(user_id=user_id, group_ids=group_ids)))


def execute_module_command(
    command_id: str,
    *,
    payload: Mapping[str, Any] | None = None,
    user_id: int | None = None,
    group_ids: set[int] | None = None,
) -> dict[str, Any] | None:
    command = _require_command(command_id)
    provider = _require_provider(command.module_id)
    return provider.execute_command(
        command=command,
        payload=dict(payload or {}),
        context=_context(user_id=user_id, group_ids=group_ids),
    )


def _context(*, user_id: int | None, group_ids: set[int] | None) -> ModuleViewContext:
    return ModuleViewContext(
        user_id=user_id,
        group_ids=frozenset(group_ids or ()),
    )


def _require_provider(module_id: str) -> ModuleViewProvider:
    get_application_registry()
    provider = _providers.get(module_id)
    if provider is None:
        raise ValueError(f"No module view provider is registered for module: {module_id}")
    return provider


def _require_view(view_id: str) -> ViewContribution:
    normalized_view_id = str(view_id or "").strip()
    for view in get_application_registry().list_views():
        if view.view_id == normalized_view_id:
            return view
    raise ValueError(f"Unknown view: {view_id}")


def _require_command(command_id: str) -> CommandContribution:
    normalized_command_id = str(command_id or "").strip()
    for command in get_application_registry().list_commands():
        if command.command_id == normalized_command_id:
            return command
    raise ValueError(f"Unknown command: {command_id}")
