from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution
from apmatia.core.runtime_paths import get_app_dir

from .collections import AI_MODEL_EXECUTOR_COLLECTION_VIEW_SPECS
from .services import (
    can_run_model,
    get_execution_record,
    get_execution_status,
    inspect_host_resources,
    list_execution_records,
    start_model,
    stop_model,
)


class ApmatiaAiModelExecutorModuleViewProvider:
    """Handles all module view operations for the AI Model Executor module."""

    def __init__(self):
        self._reservation_manager = None
        self._capacity_manager = None

    def _get_reservation_manager(self):
        if self._reservation_manager is None:
            from .reservation import ReservationManager
            from .services import _load_execution_items
            # Create a minimal repo-like object for the reservation manager
            self._reservation_manager = ReservationManager(_ExecutorRepo())
        return self._reservation_manager

    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        object_type = _object_type(view.metadata)
        if object_type == "execution":
            return self._list_executions()
        if object_type == "queue_item":
            return self._list_queue_items()
        if object_type == "reservation":
            return self._list_reservations()
        if object_type == "capacity":
            return self._list_capacity()
        if object_type == "resources":
            return self._list_resources()
        raise ValueError(f"Unsupported executor object type: {object_type}")

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        metadata = dict(command.metadata or {})
        object_type = _object_type(metadata)
        verb = str(metadata.get("verb") or "").strip().lower() or _command_verb(command.command_id)

        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command, metadata), context=context)}
        if object_type == "execution" and verb == "start":
            return self._start_execution(payload)
        if object_type == "execution" and verb == "stop":
            return self._stop_execution(payload)
        if object_type == "execution" and verb == "show":
            return self._show_execution(payload)
        if object_type == "queue_item" and verb == "enqueue":
            return self._enqueue_work(payload)
        if object_type == "queue_item" and verb == "cancel":
            return self._cancel_queue_item(payload)
        if object_type == "reservation" and verb == "create":
            return self._create_reservation(payload)
        if object_type == "reservation" and verb == "release":
            return self._release_reservation(payload)
        if object_type == "capacity" and verb == "list":
            return {"items": self._list_capacity()}
        if object_type == "resources" and verb == "inspect":
            return self._inspect_resources()
        raise ValueError(f"Unsupported executor command verb: {verb}")

    def _list_executions(self) -> list[dict[str, Any]]:
        records = list_execution_records()
        return [_execution_to_dict(r) for r in records]

    def _list_queue_items(self) -> list[dict[str, Any]]:
        from .services import _load_queue_items
        items = _load_queue_items()
        return [dict(item) for item in items]

    def _list_reservations(self) -> list[dict[str, Any]]:
        from .services import _load_reservations
        items = _load_reservations()
        return [dict(item) for item in items]

    def _list_capacity(self) -> list[dict[str, Any]]:
        from .services import list_runtimes
        runtimes = list_runtimes()
        results = []
        for runtime in runtimes:
            runtime_id = runtime.get("id", "")
            state = self._get_reservation_manager().get_admission_state(runtime_id)
            results.append({
                "runtime_id": runtime_id,
                "total_capacity": state["total_capacity"],
                "active_leases": state["active_leases"],
                "reserved_capacity": state["reserved_capacity"],
                "general_available": state["general_available"],
                "reservation_available": state["reservation_available"],
                "admission_mode": state["admission_mode"],
            })
        # Also include LLM configs as capacity entries
        llm_config_count = 0
        assigned_model_ids = set()
        agent_count = 0
        model_agent_count = {}
        try:
            from apmatia.modules.ai_model_manager.services import list_llm_configs
            from apmatia.modules.agents.runtime import get_agent_manager

            llm_configs = list_llm_configs()
            # Find which LLM configs are assigned to agents
            agent_manager = get_agent_manager()
            all_agents = agent_manager.list_agents()
            agent_count = len(all_agents)
            for agent in all_agents:
                # Collect all model IDs for this agent, then count each model once
                agent_model_ids = set()
                default_id = getattr(agent, "default_model_id", None)
                active_id = getattr(agent, "active_model_id", None)
                if default_id is not None:
                    agent_model_ids.add(int(default_id))
                if active_id is not None:
                    agent_model_ids.add(int(active_id))
                for mid in agent_model_ids:
                    assigned_model_ids.add(mid)
                    model_agent_count[mid] = model_agent_count.get(mid, 0) + 1

            for config in llm_configs:
                # list_llm_configs returns LLMConfig dataclass objects
                config_id = getattr(config, "id", None)
                if config_id is None:
                    continue
                seats = getattr(config, "seats", 1)
                if not seats or seats < 1:
                    seats = 1
                alias = getattr(config, "user_alias", "") or "Unnamed"
                provider = getattr(config, "provider_name", "")
                is_assigned = int(config_id) in assigned_model_ids
                num_agents = model_agent_count.get(int(config_id), 0)
                # Show alias as the runtime identifier for human readability
                display_name = f"{alias} ({seats} seats)"
                if provider:
                    display_name += f" - {provider}"
                if is_assigned:
                    display_name += f" [{num_agents} agent{'s' if num_agents != 1 else ''}]"
                results.append({
                    "runtime_id": display_name,
                    "total_capacity": seats,
                    "active_leases": 0,
                    "reserved_capacity": 0,
                    "general_available": seats,
                    "reservation_available": seats,
                    "admission_mode": "none",
                    "config_id": config_id,
                    "alias": alias,
                    "provider_name": provider,
                    "is_assigned": is_assigned,
                    "agent_count": num_agents,
                })
                llm_config_count += 1
        except (ImportError, AttributeError, TypeError, ValueError) as exc:
            # LLM configs might not be available if the model manager isn't loaded
            results.append({
                "runtime_id": f"_error_import",
                "total_capacity": 0,
                "active_leases": 0,
                "reserved_capacity": 0,
                "general_available": 0,
                "reservation_available": 0,
                "admission_mode": f"import_error: {exc}",
            })
        # Debug row
        results.append({
            "runtime_id": f"_debug_{llm_config_count}_configs_{agent_count}_agents",
            "total_capacity": 0,
            "active_leases": 0,
            "reserved_capacity": 0,
            "general_available": 0,
            "reservation_available": 0,
            "admission_mode": "debug",
        })
        return results

    def _list_resources(self) -> list[dict[str, Any]]:
        snapshot = inspect_host_resources()
        return [_resources_to_dict(snapshot)]

    def _start_execution(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        model_id = _require_int(payload.get("model_id"))
        port = _parse_int(payload.get("port"))
        host_id = str(payload.get("host_id") or "local")
        runtime_id = str(payload.get("runtime_id") or "")
        return start_model(model_id, host_id=host_id, runtime_id=runtime_id or None, port=port)

    def _stop_execution(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        model_id = _parse_int(payload.get("model_id"))
        execution_id = _parse_int(payload.get("execution_id"))
        host_id = str(payload.get("host_id") or "local")
        runtime_id = str(payload.get("runtime_id") or "")
        return stop_model(
            model_id=model_id,
            execution_id=execution_id,
            host_id=host_id,
            runtime_id=runtime_id or None,
        )

    def _show_execution(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        execution_id = _require_int(payload.get("execution_id"))
        record = get_execution_record(execution_id)
        if record is None:
            raise ValueError(f"Execution not found: {execution_id}")
        return _execution_to_dict(record)

    def _enqueue_work(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        from .services import enqueue_work
        return enqueue_work(
            model_id=_require_int(payload.get("model_id")),
            prompt=str(payload.get("prompt") or ""),
            priority=_parse_int(payload.get("priority"), default=0) or 0,
            runtime_id=str(payload.get("runtime_id") or ""),
            system_prompt=str(payload.get("system_prompt") or "") or None,
            max_tokens=_parse_int(payload.get("max_tokens")),
            temperature=_parse_float(payload.get("temperature")),
        )

    def _cancel_queue_item(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        from .services import cancel_queue_item
        item_id = str(payload.get("item_id") or "")
        return cancel_queue_item(item_id)

    def _create_reservation(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        from .services import request_reservation
        runtime_id = str(payload.get("runtime_id") or "")
        requested_seats = _parse_int(payload.get("requested_seats"), default=1) or 1
        mode = str(payload.get("mode") or "shared")
        owner_user_id = _parse_int(payload.get("owner_user_id"), default=1) or 1
        owner_session_id = str(payload.get("owner_session_id") or "streamlit")
        return request_reservation(
            runtime_id=runtime_id,
            owner_user_id=owner_user_id,
            owner_session_id=owner_session_id,
            requested_seats=requested_seats,
            mode=mode,
        )

    def _release_reservation(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        from .services import release_reservation
        reservation_id = str(payload.get("reservation_id") or "")
        return release_reservation(reservation_id)

    def _inspect_resources(self) -> dict[str, Any]:
        return {"items": self._list_resources()}


def _view_from_command(command: CommandContribution, metadata: Mapping[str, Any]) -> ViewContribution:
    view_id = str(metadata.get("collection_view_id") or "").strip()
    return ViewContribution(
        module_id=command.module_id,
        action_id=str(command.metadata.get("collection_view_id") or command.module_id).removesuffix(".view"),
        view_id=view_id,
        name=command.name,
        description=command.description,
        metadata=dict(command.metadata or {}),
    )


def _object_type(metadata: Mapping[str, Any]) -> str:
    object_type = str(metadata.get("object_type") or "").strip()
    if not object_type:
        raise ValueError("Module metadata is missing object_type.")
    return object_type


def _command_verb(command_id: str) -> str:
    parts = [part for part in str(command_id).split(".") if part]
    return "" if not parts else parts[-1].lower()


def _require_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as _error:
        raise ValueError("A valid item ID is required.") from _error


def _parse_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _execution_to_dict(record: Any) -> dict[str, Any]:
    from .services import _serialize_execution_record
    if hasattr(record, "__dict__"):
        return _serialize_execution_record(record)
    return dict(record)


def _resources_to_dict(snapshot: Any) -> dict[str, Any]:
    return {
        "ram_total_bytes": getattr(snapshot, "ram_total_bytes", 0),
        "ram_available_bytes": getattr(snapshot, "ram_available_bytes", 0),
        "vram_total_bytes": getattr(snapshot, "vram_total_bytes", 0),
        "vram_available_bytes": getattr(snapshot, "vram_available_bytes", 0),
        "gpu_count": getattr(snapshot, "gpu_count", 0),
        "source": getattr(snapshot, "source", "unknown"),
    }


class _ExecutorRepo:
    """Minimal repository adapter for ReservationManager."""

    def __init__(self):
        from .services import list_runtimes, _load_reservations, _load_leases
        self._runtimes = list_runtimes()
        self._reservations = _load_reservations()
        self._leases = _load_leases()

    def get_runtime(self, runtime_id: str):
        for r in self._runtimes:
            if r.get("id") == runtime_id:
                return _RuntimeDict(r)
        return None

    def get_active_reservation(self, runtime_id: str):
        for res in reversed(self._reservations):
            if res.get("runtime_id") == runtime_id and res.get("state") in ("requested", "active"):
                return res
        return None

    def get_active_leases(self, runtime_id: str):
        return [l for l in self._leases if l.get("runtime_id") == runtime_id and l.get("status") == "active"]

    def save_reservation(self, reservation):
        from .services import _load_reservations, _save_reservations
        items = _load_reservations()
        items.append(dict(reservation))
        _save_reservations(items)

    def save_lease(self, lease):
        from .services import _load_leases, _save_leases
        items = _load_leases()
        items.append(dict(lease))
        _save_leases(items)


class _RuntimeDict:
    """Thin wrapper to make a dict behave like a runtime object."""

    def __init__(self, data: dict[str, Any]):
        self.id = data.get("id", "")
        self.name = data.get("name", "")
        self.max_concurrency = int(data.get("max_concurrency", 1))
        self.endpoint_url = data.get("endpoint_url", "")
        self.state = data.get("state", "available")
