from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from apmatia.core.models import utc_now

from .models import AgentLoopTask, LoopEvent
from .ports import AgentLoopTaskRepository


class FileAgentLoopTaskRepository(AgentLoopTaskRepository):
    def __init__(self, root: Path) -> None:
        self.root = root
        self.tasks_dir = self.root / "tasks"
        self.events_dir = self.root / "events"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def get(self, task_id: str) -> AgentLoopTask | None:
        path = self._task_path(task_id)
        if not path.exists():
            return None
        try:
            raw_payload = path.read_text(encoding="utf-8")
        except OSError:
            return None
        if not raw_payload.strip():
            return None
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            return None
        return AgentLoopTask.from_dict(payload)

    def save(self, task: AgentLoopTask) -> None:
        task_path = self._task_path(str(task.id or ""))
        task_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(task.to_dict(), indent=2, ensure_ascii=False)
        task_path.write_text(serialized, encoding="utf-8")

    def append_event(self, task_id: str, event: LoopEvent) -> None:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"Task not found: {task_id}")

        updated = replace(task, events=(*task.events, event), updated_at=utc_now())
        self.save(updated)

        event_path = self._events_path(task_id)
        event_path.parent.mkdir(parents=True, exist_ok=True)
        with event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False))
            handle.write("\n")

    def list_all(self) -> list[AgentLoopTask]:
        tasks: list[AgentLoopTask] = []
        for path in sorted(self.tasks_dir.glob("*.json")):
            try:
                tasks.append(AgentLoopTask.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        tasks.sort(key=lambda task: str(task.updated_at), reverse=True)
        return tasks

    def _task_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def _events_path(self, task_id: str) -> Path:
        return self.events_dir / f"{task_id}.jsonl"


class InMemoryAgentLoopTaskRepository(AgentLoopTaskRepository):
    def __init__(self) -> None:
        self._tasks: dict[str, AgentLoopTask] = {}

    def get(self, task_id: str) -> AgentLoopTask | None:
        return self._tasks.get(task_id)

    def save(self, task: AgentLoopTask) -> None:
        self._tasks[str(task.id or "")] = task

    def append_event(self, task_id: str, event: LoopEvent) -> None:
        task = self._tasks[task_id]
        self._tasks[task_id] = replace(task, events=(*task.events, event), updated_at=utc_now())

    def list_all(self) -> list[AgentLoopTask]:
        tasks = list(self._tasks.values())
        tasks.sort(key=lambda task: str(task.updated_at), reverse=True)
        return tasks
