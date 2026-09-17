from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from threading import RLock
from typing import Any

from apmatia.core.models import utc_now
from apmatia.modules.persistence import SQLiteStore

from .models import AgentLoopTask, LoopEvent
from .ports import AgentLoopTaskRepository
from .state import resolve_agent_loop_workspace_root


@dataclass(frozen=True, slots=True)
class LoopTaskTables:
    tasks: str = "loop_tasks"
    events: str = "loop_task_events"


class SQLiteLoopTaskRepository(AgentLoopTaskRepository):
    """SQLite-backed task and ordered transcript repository."""

    def __init__(self, store: SQLiteStore, tables: LoopTaskTables) -> None:
        self._store = store
        self._tables = tables
        self._lock = RLock()

    def create(self, task: AgentLoopTask) -> AgentLoopTask:
        task_id = _task_id(task)
        with self._lock:
            if self._store.get(self._tables.tasks, task_id=task_id) is not None:
                raise ValueError(f"Task already exists: {task_id}")
            normalized = replace(task, id=task_id, next_event_sequence=max(1, task.next_event_sequence))
            self._store.insert(self._tables.tasks, _task_payload(normalized))
            return normalized

    def get(self, task_id: str) -> AgentLoopTask | None:
        normalized_id = str(task_id or "").strip()
        if not normalized_id:
            return None
        with self._lock:
            row = self._store.get(self._tables.tasks, task_id=normalized_id)
            if row is None:
                return None
            task = _row_to_task(row)
            return self._with_events_and_reconciled_sequence(task)

    def update(self, task: AgentLoopTask) -> None:
        task_id = _task_id(task)
        with self._lock:
            if self._store.get(self._tables.tasks, task_id=task_id) is None:
                raise ValueError(f"Task not found: {task_id}")
            self._store.update(self._tables.tasks, {"task_id": task_id}, _task_payload(task))

    def save(self, task: AgentLoopTask) -> None:
        task_id = _task_id(task)
        with self._lock:
            if self._store.get(self._tables.tasks, task_id=task_id) is None:
                self.create(task)
            else:
                self.update(task)

    def list_tasks(
        self,
        *,
        agent_id: int | None = None,
        include_archived: bool = False,
    ) -> list[AgentLoopTask]:
        with self._lock:
            tasks = [
                self._with_events_and_reconciled_sequence(_row_to_task(row))
                for row in self._store.find(self._tables.tasks)
            ]
        if agent_id is not None:
            tasks = [task for task in tasks if task.agent_id == int(agent_id)]
        if not include_archived:
            tasks = [task for task in tasks if task.status.value != "archived"]
        tasks.sort(key=lambda task: task.updated_at, reverse=True)
        return tasks

    def list_all(self) -> list[AgentLoopTask]:
        return self.list_tasks(include_archived=True)

    def append_ordered_event(self, task_id: str, event: LoopEvent) -> LoopEvent:
        normalized_id = str(task_id or "").strip()
        with self._lock:
            task = self.get(normalized_id)
            if task is None:
                raise KeyError(f"Task not found: {normalized_id}")
            next_sequence = max(
                1,
                int(task.next_event_sequence or 1),
                self._largest_event_sequence(normalized_id) + 1,
            )
            ordered_event = replace(event, task_id=normalized_id, sequence=next_sequence)
            self._store.insert(self._tables.events, _event_payload(ordered_event))
            self._store.update(
                self._tables.tasks,
                {"task_id": normalized_id},
                {"next_event_sequence": next_sequence + 1, "updated_at": utc_now().isoformat()},
            )
            return ordered_event

    def append_event(self, task_id: str, event: LoopEvent) -> None:
        self.append_ordered_event(task_id, event)

    def list_ordered_events(self, task_id: str, *, after_sequence: int = 0) -> list[LoopEvent]:
        normalized_id = str(task_id or "").strip()
        with self._lock:
            rows = self._store.find(self._tables.events, task_id=normalized_id)
        events = [_row_to_event(row) for row in rows]
        events.sort(key=lambda event: event.sequence or 0)
        return [event for event in events if (event.sequence or 0) > int(after_sequence)]

    def reconcile_next_event_sequence(self, task_id: str) -> int:
        normalized_id = str(task_id or "").strip()
        with self._lock:
            row = self._store.get(self._tables.tasks, task_id=normalized_id)
            if row is None:
                raise KeyError(f"Task not found: {normalized_id}")
            next_sequence = max(
                1,
                int(row.get("next_event_sequence") or 1),
                self._largest_event_sequence(normalized_id) + 1,
            )
            if int(row.get("next_event_sequence") or 1) != next_sequence:
                self._store.update(
                    self._tables.tasks,
                    {"task_id": normalized_id},
                    {"next_event_sequence": next_sequence},
                )
            return next_sequence

    def _largest_event_sequence(self, task_id: str) -> int:
        rows = self._store.find(self._tables.events, task_id=task_id)
        return max((int(row.get("sequence") or 0) for row in rows), default=0)

    def _with_events_and_reconciled_sequence(self, task: AgentLoopTask) -> AgentLoopTask:
        events = tuple(self.list_ordered_events(str(task.id or "")))
        next_sequence = self.reconcile_next_event_sequence(str(task.id or ""))
        if task.events == events and task.next_event_sequence == next_sequence:
            return task
        return replace(task, events=events, next_event_sequence=next_sequence)


class SQLiteLoopTaskBundle:
    """Persistence bundle for Agent Loops' dedicated loop_tasks database."""

    def __init__(
        self,
        store: SQLiteStore | str | Path | None = None,
        *,
        db_path: str | Path | None = None,
        tables: LoopTaskTables | None = None,
    ) -> None:
        if store is not None and db_path is not None:
            raise ValueError("Pass either store or db_path, not both.")
        self.tables = tables or LoopTaskTables()
        if store is None:
            store = db_path or (resolve_agent_loop_workspace_root() / "loop_tasks.db")
        self.store = store if isinstance(store, SQLiteStore) else SQLiteStore(store)
        self.tasks = SQLiteLoopTaskRepository(self.store, self.tables)


def _task_id(task: AgentLoopTask) -> str:
    task_id = str(task.id or "").strip()
    if not task_id:
        raise ValueError("Cannot persist a task without an id.")
    return task_id


def _task_payload(task: AgentLoopTask) -> dict[str, Any]:
    payload = task.to_dict()
    payload["task_id"] = _task_id(task)
    payload.pop("id", None)
    # Events have their own ordered table and are reconstructed on read.
    payload.pop("events", None)
    return payload


def _event_payload(event: LoopEvent) -> dict[str, Any]:
    payload = event.to_dict()
    payload["task_id"] = event.task_id
    return payload


def _row_to_task(row: dict[str, Any]) -> AgentLoopTask:
    payload = dict(row)
    payload.pop("id", None)
    payload["id"] = payload.get("task_id")
    return AgentLoopTask.from_dict(payload)


def _row_to_event(row: dict[str, Any]) -> LoopEvent:
    payload = dict(row)
    payload["task_id"] = payload.get("task_id") or ""
    return LoopEvent.from_dict(payload)
