from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date, datetime, time
from typing import Any

from apmatia.core.agent_management_runtime import get_agent_manager
from apmatia.core.model_management_runtime import get_llm_config_manager
from apmatia.core.settings_service import resolve_timezone
from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution

from .service import AgentAlarmsService, get_agent_alarm_service


class AgentAlarmsModuleViewProvider:
    def __init__(
        self,
        service: AgentAlarmsService | None = None,
        service_factory: Callable[[], AgentAlarmsService] | None = None,
    ) -> None:
        self._service = service
        self._service_factory = service_factory

    @property
    def service(self) -> AgentAlarmsService:
        if self._service is None:
            if self._service_factory is None:
                self._service = get_agent_alarm_service()
            else:
                self._service = self._service_factory()
        return self._service

    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        return self.service.list_alarm_items()

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        verb = str((command.metadata or {}).get("verb") or "").strip().lower()
        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command), context=context)}
        if verb == "create":
            normalized_payload = _normalize_alarm_payload(dict(payload))
            alarm = self.service.create_alarm(
                name=str(normalized_payload.get("name") or ""),
                agent_id=_required_int(normalized_payload.get("agent_id"), field_name="agent_id"),
                prompt=str(normalized_payload.get("prompt") or ""),
                model_id=_required_int(normalized_payload.get("model_id"), field_name="model_id"),
                scheduled_start_time=normalized_payload.get("scheduled_start_time") or "",
                enabled=normalized_payload.get("enabled", True),
            )
            return {"status": "created", "item": self.service.serialize_alarm(alarm)}
        if verb == "edit":
            alarm_id = _required_int(payload.get("item_id"), field_name="item_id")
            updates = _normalize_alarm_payload(dict(payload))
            updates.pop("item_id", None)
            alarm = self.service.update_alarm(alarm_id, **updates)
            return {"status": "updated", "item": self.service.serialize_alarm(alarm)}
        if verb == "delete":
            alarm_id = _required_int(payload.get("item_id"), field_name="item_id")
            deleted = self.service.delete_alarm(alarm_id)
            return {"status": "deleted" if deleted else "not_found", "deleted": deleted, "item_id": alarm_id}
        raise ValueError(f"Unsupported alarm command verb: {verb}")


def _view_from_command(command: CommandContribution) -> ViewContribution:
    return ViewContribution(
        module_id=command.module_id,
        action_id=command.action_id,
        view_id="agent_alarms.alarms.view",
        name="Agent Alarms",
        description="Schedule autonomous alarm-style agent runs.",
        metadata={},
    )


def _normalize_alarm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "agent_id" in normalized:
        normalized["agent_id"] = _resolve_agent_id(normalized["agent_id"])
    if "model_id" in normalized:
        normalized["model_id"] = _resolve_model_id(normalized["model_id"])

    scheduled_start_time = _combine_scheduled_start_time(normalized)
    if scheduled_start_time is not None:
        normalized["scheduled_start_time"] = scheduled_start_time
    return normalized


def _resolve_agent_id(value: Any) -> int:
    candidate = _extract_option_value(value)
    if candidate is None:
        raise ValueError("A valid agent_id is required.")
    try:
        return int(candidate)
    except (TypeError, ValueError):
        pass

    agents = get_agent_manager().list_agents()
    for agent in agents:
        if str(getattr(agent, "name", "")).strip() == str(candidate).strip():
            return int(getattr(agent, "id"))
    raise ValueError("A valid agent_id is required.")


def _resolve_model_id(value: Any) -> int:
    candidate = _extract_option_value(value)
    if candidate is None:
        raise ValueError("A valid model_id is required.")
    try:
        return int(candidate)
    except (TypeError, ValueError):
        pass

    configs = get_llm_config_manager().list_configs()
    for config in configs:
        alias = str(getattr(config, "user_alias", "")).strip()
        if alias and alias == str(candidate).strip():
            return int(getattr(config, "id"))
    raise ValueError("A valid model_id is required.")


def _combine_scheduled_start_time(payload: Mapping[str, Any]) -> str | datetime | None:
    raw_date = payload.get("scheduled_start_date")
    raw_time = payload.get("scheduled_start_time")
    if raw_date in (None, "") and raw_time in (None, ""):
        return payload.get("scheduled_start_time") if "scheduled_start_time" in payload else None

    date_value = _coerce_date(raw_date)
    time_value = _coerce_time(raw_time)
    if date_value is None or time_value is None:
        return None
    local_tz = resolve_timezone()
    return datetime.combine(date_value, time_value, tzinfo=local_tz).isoformat(timespec="minutes")


def _coerce_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value.strip():
        raw = value.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            try:
                return datetime.fromisoformat(raw).date()
            except ValueError:
                return None
    return None


def _coerce_time(value: Any) -> time | None:
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.timetz() if value.tzinfo is not None else value.time()
    if isinstance(value, str) and value.strip():
        raw = value.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            try:
                return time.fromisoformat(raw)
            except ValueError:
                return None
        return parsed.timetz() if parsed.tzinfo is not None else parsed.time()
    return None


def _extract_option_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        if "value" in value:
            return value.get("value")
        if "id" in value:
            return value.get("id")
    return value


def _required_int(value: Any, *, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"A valid {field_name} is required.") from error
