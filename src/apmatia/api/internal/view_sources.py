"""API-owned providers for rich, renderer-neutral view data sources."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from apmatia.api.internal.agent_management import list_agents
from apmatia.api.internal.model_management import list_llm_configs
from apmatia.api.internal.module_views import get_module_view_items


def load_view_source(operation: str, *, user_id: int, parameters: dict[str, Any] | None = None) -> Any:
    """Resolve a declared source operation without exposing module internals to clients."""
    params = dict(parameters or {})
    if operation in {"agents:list", "list_agents"}:
        return [_serialize(agent) for agent in list_agents()]
    if operation in {"model_configs:list", "list_llm_configs"}:
        return [_serialize(config) for config in list_llm_configs()]
    if operation == "preferences:list_catalog":
        return get_module_view_items("preferences.modules.view", user_id=user_id)
    raise ValueError(f"Unsupported view source operation: {operation}")


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value
