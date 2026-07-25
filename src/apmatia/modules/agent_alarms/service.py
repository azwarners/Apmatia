from __future__ import annotations

import atexit
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Protocol

from apmatia.modules.agents.runtime import get_agent_manager
from apmatia.core.model_management_runtime import get_llm_config_manager
from apmatia.core.runtime_paths import get_data_dir
from apmatia.lib.apmatia_core.models import utc_now
from apmatia.modules.agent_loops import get_agent_loop_run, start_agent_loop

from .models import AlarmStatus, AgentAlarm
from .repositories import AgentAlarmRepository, SQLiteAgentAlarmRepository


class AlarmLoopService(Protocol):
    def start_loop(self, *, agent_id: int, prompt: str, model_id: int | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def get_loop_run(self, run_id: str) -> dict[str, Any] | None:
        raise NotImplementedError


class AgentAlarmsService:
    def __init__(
        self,
        repository: AgentAlarmRepository | None = None,
        loop_service: AlarmLoopService | None = None,
        *,
        poll_interval_seconds: float = 5.0,
        data_dir: Path | None = None,
    ) -> None:
        root = data_dir or get_data_dir()
        self._repository = repository or SQLiteAgentAlarmRepository(root / "agent_alarms.db")
        self._loop_service = loop_service or _DefaultAlarmLoopService()
        self._poll_interval_seconds = max(0.5, float(poll_interval_seconds))
        self._lock = Lock()
        self._stop_event = Event()
        self._scheduler_thread: Thread | None = None

    def ensure_started(self) -> None:
        with self._lock:
            if self._scheduler_thread is not None and self._scheduler_thread.is_alive():
                return
            self._stop_event.clear()
            self._scheduler_thread = Thread(target=self._run_scheduler, name="apmatia-agent-alarms", daemon=True)
            self._scheduler_thread.start()

    def shutdown(self) -> None:
        self._stop_event.set()
        with self._lock:
            thread = self._scheduler_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)

    def list_alarms(self) -> list[AgentAlarm]:
        return self._repository.list_all()

    def list_alarm_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for alarm in self.list_alarms():
            item = self.serialize_alarm(alarm)
            run_id = str(alarm.launched_loop_run_id or "").strip()
            if run_id:
                run = self._loop_service.get_loop_run(run_id)
                if isinstance(run, dict):
                    item["loop_run_status"] = _loop_status(run)
                    item["loop_run_summary"] = _result_summary(run)
                    item["loop_run_error"] = _failure_message(run) if _loop_status(run) not in {"completed", "running", "queued", "pending"} else ""
            items.append(item)
        items.sort(key=lambda item: (str(item.get("scheduled_start_time") or ""), str(item.get("created_at") or ""), str(item.get("id") or "")))
        return items

    def get_alarm(self, alarm_id: int) -> AgentAlarm | None:
        return self._repository.get(alarm_id)

    def serialize_alarm(self, alarm: AgentAlarm) -> dict[str, Any]:
        item = alarm.to_dict()
        item["status"] = alarm.status.value
        item["status_label"] = alarm.status.value.replace("_", " ").title()
        item["enabled_label"] = "Enabled" if alarm.enabled else "Disabled"
        item["scheduled_start_time_display"] = alarm.scheduled_start_time.isoformat(timespec="minutes")
        item["started_at_display"] = None if alarm.started_at is None else alarm.started_at.isoformat(timespec="seconds")
        item["completed_at_display"] = None if alarm.completed_at is None else alarm.completed_at.isoformat(timespec="seconds")
        item["agent_name"] = _agent_label(int(alarm.agent_id))
        item["model_name"] = _model_label(int(alarm.model_id))
        item["result_summary"] = _summary_preview(alarm.last_result)
        item["error_summary"] = _summary_preview(alarm.last_error)
        return item

    def create_alarm(
        self,
        *,
        name: str,
        agent_id: int,
        prompt: str,
        model_id: int,
        scheduled_start_time: datetime | str,
        enabled: bool = True,
    ) -> AgentAlarm:
        enabled_value = _coerce_bool(enabled, True)
        alarm = AgentAlarm(
            id=None,
            name=name,
            agent_id=agent_id,
            prompt=prompt,
            model_id=model_id,
            scheduled_start_time=scheduled_start_time,
            enabled=enabled_value,
            status=AlarmStatus.SCHEDULED if enabled_value else AlarmStatus.DISABLED,
        )
        alarm_id = self._repository.create(alarm)
        created = self._repository.get(alarm_id)
        if created is None:
            raise ValueError("Failed to load created alarm.")
        return created

    def update_alarm(self, alarm_id: int, **updates: Any) -> AgentAlarm:
        current = self._require_alarm(alarm_id)
        merged = self._apply_updates(current, updates)
        self._repository.update(merged)
        return merged

    def delete_alarm(self, alarm_id: int) -> bool:
        return self._repository.delete(alarm_id)

    def poll_once(self) -> None:
        now = utc_now()
        self._launch_due_alarms(now)
        self._refresh_running_alarms()

    def _run_scheduler(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception:
                pass
            self._stop_event.wait(self._poll_interval_seconds)

    def _launch_due_alarms(self, now: datetime) -> None:
        for alarm in self._repository.list_due(now):
            claimed = self._repository.claim_due_alarm(alarm.id or 0, now)
            if claimed is None:
                continue
            self._launch_alarm(claimed)

    def _launch_alarm(self, alarm: AgentAlarm) -> None:
        try:
            run = self._loop_service.start_loop(
                agent_id=int(alarm.agent_id),
                prompt=alarm.prompt,
                model_id=int(alarm.model_id),
            )
            run_id = _loop_run_id(run)
            updated = replace(
                alarm,
                launched_loop_run_id=run_id,
                updated_at=utc_now(),
            )
            self._repository.update(updated)
        except Exception as exc:
            failed = replace(
                alarm,
                status=AlarmStatus.FAILED,
                enabled=False,
                completed_at=utc_now(),
                last_error=str(exc),
                updated_at=utc_now(),
            )
            self._repository.update(failed)

    def _refresh_running_alarms(self) -> None:
        for alarm in self._repository.list_tracking():
            run_id = str(alarm.launched_loop_run_id or "").strip()
            if not run_id:
                continue
            run = self._loop_service.get_loop_run(run_id)
            if run is None:
                self._mark_failed(alarm, f"Loop run not found: {run_id}")
                continue

            run_status = _loop_status(run)
            if run_status in {"running", "queued", "pending"}:
                continue
            if run_status == "completed":
                self._mark_completed(alarm, run)
                continue
            self._mark_failed(alarm, _failure_message(run))

    def _mark_completed(self, alarm: AgentAlarm, run: dict[str, Any]) -> None:
        completed = replace(
            alarm,
            status=AlarmStatus.COMPLETED,
            enabled=False,
            completed_at=utc_now(),
            last_result=_result_summary(run),
            last_error=None,
            updated_at=utc_now(),
        )
        self._repository.update(completed)

    def _mark_failed(self, alarm: AgentAlarm, message: str) -> None:
        failed = replace(
            alarm,
            status=AlarmStatus.FAILED,
            enabled=False,
            completed_at=utc_now(),
            last_error=message,
            updated_at=utc_now(),
        )
        self._repository.update(failed)

    def _require_alarm(self, alarm_id: int) -> AgentAlarm:
        alarm = self._repository.get(alarm_id)
        if alarm is None:
            raise ValueError(f"Alarm not found: {alarm_id}")
        return alarm

    def _apply_updates(self, alarm: AgentAlarm, updates: dict[str, Any]) -> AgentAlarm:
        status_value = updates.get("status", alarm.status)
        enabled_value = updates.get("enabled", alarm.enabled)
        status = alarm.status
        if isinstance(status_value, AlarmStatus):
            status = status_value
        elif isinstance(status_value, str) and status_value.strip():
            try:
                status = AlarmStatus(status_value.strip().lower())
            except ValueError:
                status = alarm.status

        merged = replace(
            alarm,
            name=str(updates.get("name", alarm.name)),
            agent_id=_coerce_int(updates.get("agent_id"), alarm.agent_id),
            prompt=str(updates.get("prompt", alarm.prompt)),
            model_id=_coerce_int(updates.get("model_id"), alarm.model_id),
            scheduled_start_time=updates.get("scheduled_start_time", alarm.scheduled_start_time),
            enabled=_coerce_bool(enabled_value, alarm.enabled),
            status=status,
            started_at=updates.get("started_at", alarm.started_at),
            completed_at=updates.get("completed_at", alarm.completed_at),
            launched_loop_run_id=updates.get("launched_loop_run_id", alarm.launched_loop_run_id),
            last_result=updates.get("last_result", alarm.last_result),
            last_error=updates.get("last_error", alarm.last_error),
            updated_at=utc_now(),
        )

        if merged.status == AlarmStatus.SCHEDULED or merged.enabled:
            merged = replace(
                merged,
                status=AlarmStatus.SCHEDULED,
                enabled=True,
                started_at=None,
                completed_at=None,
                launched_loop_run_id=None,
                last_result=None,
                last_error=None,
            )
        elif merged.status == AlarmStatus.DISABLED or not merged.enabled:
            merged = replace(merged, status=AlarmStatus.DISABLED, enabled=False)
        return merged


class _DefaultAlarmLoopService:
    def start_loop(self, *, agent_id: int, prompt: str, model_id: int | None = None) -> dict[str, Any]:
        return start_agent_loop(agent_id=agent_id, prompt=prompt, model_id=model_id)

    def get_loop_run(self, run_id: str) -> dict[str, Any] | None:
        return get_agent_loop_run(run_id)


_service: AgentAlarmsService | None = None
_atexit_registered = False


def get_agent_alarm_service() -> AgentAlarmsService:
    global _service
    global _atexit_registered

    if _service is None:
        _service = AgentAlarmsService()
    _service.ensure_started()
    if not _atexit_registered:
        atexit.register(shutdown_agent_alarm_service)
        _atexit_registered = True
    return _service


def shutdown_agent_alarm_service() -> None:
    if _service is not None:
        _service.shutdown()


def _loop_run_id(run: dict[str, Any]) -> str:
    run_id = run.get("id")
    if run_id in (None, ""):
        run_id = run.get("run_id")
    if run_id in (None, ""):
        raise ValueError("Agent loop run did not return an identifier.")
    return str(run_id)


def _loop_status(run: dict[str, Any]) -> str:
    status = str(run.get("execution_status") or run.get("status") or "").strip().lower()
    if status:
        return status
    task = run.get("task")
    if isinstance(task, dict):
        return str(task.get("execution_status") or task.get("status") or "").strip().lower()
    return ""


def _result_summary(run: dict[str, Any]) -> str:
    task = run.get("task") if isinstance(run.get("task"), dict) else {}
    summary = str(
        run.get("summary")
        or (task.get("summary") if isinstance(task, dict) else "")
        or (task.get("final_text") if isinstance(task, dict) else "")
        or run.get("final_text")
        or ""
    ).strip()
    if not summary and isinstance(run.get("raw_response"), dict):
        summary = str(run["raw_response"].get("reply_text") or "").strip()
    return summary[:500]


def _failure_message(run: dict[str, Any]) -> str:
    message = str(
        run.get("last_error")
        or (run.get("task", {}) or {}).get("last_error")
        or run.get("error")
        or _result_summary(run)
        or "Agent loop failed."
    ).strip()
    return message[:500]


def _summary_preview(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[:160]


def _coerce_int(value: Any, default: int) -> int:
    try:
        if value in (None, ""):
            return int(default)
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _coerce_bool(value: Any, default: bool) -> bool:
    if value in (None, ""):
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    return bool(default)


def _agent_label(agent_id: int) -> str:
    agent = get_agent_manager().get_agent(agent_id)
    if agent is None:
        return f"Agent {agent_id}"
    return str(agent.name or f"Agent {agent_id}")


def _model_label(model_id: int) -> str:
    model = get_llm_config_manager().get_config(model_id)
    if model is None:
        return f"Model {model_id}"
    return str(model.user_alias or model.provider_name or model.model_name or f"Model {model_id}")
