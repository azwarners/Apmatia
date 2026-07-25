from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from apmatia.modules.persistence import SQLiteStore

from apmatia.lib.apmatia_core.models import utc_now

from .models import CalendarEvent, CapturedIdea, Habit, IpeProject, IpeTask
from .repositories import (
    CalendarEventRepository,
    CapturedIdeaRepository,
    HabitRepository,
    IpeProjectRepository,
    IpeTaskRepository,
)


@dataclass(frozen=True, slots=True)
class IpeTables:
    ideas: str = "ipe_captured_ideas"
    tasks: str = "ipe_tasks"
    projects: str = "ipe_projects"
    habits: str = "ipe_habits"
    calendar_events: str = "ipe_calendar_events"


class SQLiteCapturedIdeaRepository(CapturedIdeaRepository):
    def __init__(self, store: SQLiteStore, tables: IpeTables):
        self._store = store
        self._tables = tables

    def create(self, idea: CapturedIdea) -> int:
        return self._store.insert(self._tables.ideas, _idea_payload(idea))

    def get(self, idea_id: int) -> CapturedIdea | None:
        row = self._store.get(self._tables.ideas, id=idea_id)
        return None if row is None else _row_to_idea(row)

    def list_all(self) -> list[CapturedIdea]:
        return [_row_to_idea(row) for row in self._store.find(self._tables.ideas)]

    def update(self, idea: CapturedIdea) -> None:
        if idea.id is None:
            raise ValueError("Cannot update idea without an id.")
        self._store.update(self._tables.ideas, {"id": idea.id}, _idea_payload(idea))

    def delete(self, idea_id: int) -> bool:
        return self._store.delete(self._tables.ideas, id=idea_id) > 0


class SQLiteIpeTaskRepository(IpeTaskRepository):
    def __init__(self, store: SQLiteStore, tables: IpeTables):
        self._store = store
        self._tables = tables

    def create(self, task: IpeTask) -> int:
        return self._store.insert(self._tables.tasks, _task_payload(task))

    def get(self, task_id: int) -> IpeTask | None:
        row = self._store.get(self._tables.tasks, id=task_id)
        return None if row is None else _row_to_task(row)

    def list_all(self) -> list[IpeTask]:
        return [_row_to_task(row) for row in self._store.find(self._tables.tasks)]

    def update(self, task: IpeTask) -> None:
        if task.id is None:
            raise ValueError("Cannot update task without an id.")
        self._store.update(self._tables.tasks, {"id": task.id}, _task_payload(task))

    def delete(self, task_id: int) -> bool:
        return self._store.delete(self._tables.tasks, id=task_id) > 0


class SQLiteIpeProjectRepository(IpeProjectRepository):
    def __init__(self, store: SQLiteStore, tables: IpeTables):
        self._store = store
        self._tables = tables

    def create(self, project: IpeProject) -> int:
        return self._store.insert(self._tables.projects, _project_payload(project))

    def get(self, project_id: int) -> IpeProject | None:
        row = self._store.get(self._tables.projects, id=project_id)
        return None if row is None else _row_to_project(row)

    def list_all(self) -> list[IpeProject]:
        return [_row_to_project(row) for row in self._store.find(self._tables.projects)]

    def update(self, project: IpeProject) -> None:
        if project.id is None:
            raise ValueError("Cannot update project without an id.")
        self._store.update(self._tables.projects, {"id": project.id}, _project_payload(project))

    def delete(self, project_id: int) -> bool:
        return self._store.delete(self._tables.projects, id=project_id) > 0


class SQLiteHabitRepository(HabitRepository):
    def __init__(self, store: SQLiteStore, tables: IpeTables):
        self._store = store
        self._tables = tables

    def create(self, habit: Habit) -> int:
        return self._store.insert(self._tables.habits, _habit_payload(habit))

    def get(self, habit_id: int) -> Habit | None:
        row = self._store.get(self._tables.habits, id=habit_id)
        return None if row is None else _row_to_habit(row)

    def list_all(self) -> list[Habit]:
        return [_row_to_habit(row) for row in self._store.find(self._tables.habits)]

    def update(self, habit: Habit) -> None:
        if habit.id is None:
            raise ValueError("Cannot update habit without an id.")
        self._store.update(self._tables.habits, {"id": habit.id}, _habit_payload(habit))

    def delete(self, habit_id: int) -> bool:
        return self._store.delete(self._tables.habits, id=habit_id) > 0


class SQLiteCalendarEventRepository(CalendarEventRepository):
    def __init__(self, store: SQLiteStore, tables: IpeTables):
        self._store = store
        self._tables = tables

    def create(self, event: CalendarEvent) -> int:
        return self._store.insert(self._tables.calendar_events, _event_payload(event))

    def get(self, event_id: int) -> CalendarEvent | None:
        row = self._store.get(self._tables.calendar_events, id=event_id)
        return None if row is None else _row_to_event(row)

    def list_all(self) -> list[CalendarEvent]:
        return [_row_to_event(row) for row in self._store.find(self._tables.calendar_events)]

    def update(self, event: CalendarEvent) -> None:
        if event.id is None:
            raise ValueError("Cannot update event without an id.")
        self._store.update(self._tables.calendar_events, {"id": event.id}, _event_payload(event))

    def delete(self, event_id: int) -> bool:
        return self._store.delete(self._tables.calendar_events, id=event_id) > 0


class SQLiteIpeBundle:
    def __init__(self, store: SQLiteStore | str | Path, tables: IpeTables | None = None):
        self.tables = tables or IpeTables()
        self.store = SQLiteStore(store) if not isinstance(store, SQLiteStore) else store
        self.ideas = SQLiteCapturedIdeaRepository(self.store, self.tables)
        self.tasks = SQLiteIpeTaskRepository(self.store, self.tables)
        self.projects = SQLiteIpeProjectRepository(self.store, self.tables)
        self.habits = SQLiteHabitRepository(self.store, self.tables)
        self.calendar_events = SQLiteCalendarEventRepository(self.store, self.tables)


def _base_payload(
    obj: CapturedIdea | IpeTask | IpeProject | Habit | CalendarEvent,
) -> dict[str, Any]:
    return {
        "id": obj.id,
        "owner_user_id": obj.owner_user_id,
        "owner_group_id": obj.owner_group_id,
        "mode": obj.mode,
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
        "status": obj.status,
        "source_idea_id": obj.source_idea_id,
    }


def _idea_payload(idea: CapturedIdea) -> dict[str, Any]:
    payload = _base_payload(idea)
    payload.update(
        {
            "title": idea.title,
            "body": idea.body,
            "captured_at": idea.captured_at.isoformat(),
            "source": idea.source,
            "tags": list(idea.tags),
            "converted_to_type": idea.converted_to_type,
            "converted_to_id": idea.converted_to_id,
            "converted_at": idea.converted_at.isoformat() if idea.converted_at else None,
        }
    )
    return payload


def _task_payload(task: IpeTask) -> dict[str, Any]:
    payload = _base_payload(task)
    payload.update(
        {
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "project_id": task.project_id,
            "due_at": task.due_at.isoformat() if task.due_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "tags": list(task.tags),
        }
    )
    return payload


def _project_payload(project: IpeProject) -> dict[str, Any]:
    payload = _base_payload(project)
    payload.update(
        {
            "name": project.name,
            "description": project.description,
            "started_on": project.started_on.isoformat() if project.started_on else None,
            "target_on": project.target_on.isoformat() if project.target_on else None,
            "source_task_id": project.source_task_id,
            "tags": list(project.tags),
            "workspace_root": project.workspace_root,
        }
    )
    return payload


def _habit_payload(habit: Habit) -> dict[str, Any]:
    payload = _base_payload(habit)
    payload.update(
        {
            "name": habit.name,
            "cadence": habit.cadence,
            "target_count": habit.target_count,
            "streak_count": habit.streak_count,
            "active": habit.active,
            "last_completed_on": habit.last_completed_on.isoformat() if habit.last_completed_on else None,
            "completion_timestamps": [timestamp.isoformat() for timestamp in habit.completion_timestamps],
            "tags": list(habit.tags),
        }
    )
    return payload


def _event_payload(event: CalendarEvent) -> dict[str, Any]:
    payload = _base_payload(event)
    payload.update(
        {
            "title": event.title,
            "start_at": event.start_at.isoformat() if event.start_at else None,
            "end_at": event.end_at.isoformat() if event.end_at else None,
            "description": event.description,
            "location": event.location,
            "all_day": event.all_day,
            "attendee_ids": list(event.attendee_ids),
            "tags": list(event.tags),
        }
    )
    return payload


def _row_to_idea(row: dict[str, Any]) -> CapturedIdea:
    return CapturedIdea(
        id=_parse_int(row.get("id")),
        owner_user_id=_parse_int(row.get("owner_user_id")),
        owner_group_id=_parse_int(row.get("owner_group_id")),
        mode=_parse_int(row.get("mode")) or 0,
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
        status=str(row.get("status", "captured")),
        source_idea_id=_parse_id_value(row.get("source_idea_id")),
        title=str(row.get("title", "")),
        body=str(row.get("body", "")),
        captured_at=_parse_datetime(row.get("captured_at")),
        source=str(row.get("source", "manual")),
        tags=_parse_string_tuple(row.get("tags")),
        converted_to_type=_optional_str(row.get("converted_to_type")),
        converted_to_id=_parse_id_value(row.get("converted_to_id")),
        converted_at=_parse_datetime_or_none(row.get("converted_at")),
    )


def _row_to_task(row: dict[str, Any]) -> IpeTask:
    return IpeTask(
        id=_parse_int(row.get("id")),
        owner_user_id=_parse_int(row.get("owner_user_id")),
        owner_group_id=_parse_int(row.get("owner_group_id")),
        mode=_parse_int(row.get("mode")) or 0,
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
        status=str(row.get("status", "todo")),
        source_idea_id=_parse_id_value(row.get("source_idea_id")),
        title=str(row.get("title", "")),
        description=str(row.get("description", "")),
        priority=int(row.get("priority", 3)),
        project_id=_parse_id_value(row.get("project_id")),
        due_at=_parse_datetime_or_none(row.get("due_at")),
        completed_at=_parse_datetime_or_none(row.get("completed_at")),
        tags=_parse_string_tuple(row.get("tags")),
    )


def _row_to_project(row: dict[str, Any]) -> IpeProject:
    return IpeProject(
        id=_parse_int(row.get("id")),
        owner_user_id=_parse_int(row.get("owner_user_id")),
        owner_group_id=_parse_int(row.get("owner_group_id")),
        mode=_parse_int(row.get("mode")) or 0,
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
        status=str(row.get("status", "active")),
        source_idea_id=_parse_id_value(row.get("source_idea_id")),
        name=str(row.get("name", "")),
        description=str(row.get("description", "")),
        started_on=_parse_date_or_none(row.get("started_on")),
        target_on=_parse_date_or_none(row.get("target_on")),
        source_task_id=_parse_id_value(row.get("source_task_id")),
        tags=_parse_string_tuple(row.get("tags")),
        workspace_root=str(row.get("workspace_root", "")),
    )


def _row_to_habit(row: dict[str, Any]) -> Habit:
    return Habit(
        id=_parse_int(row.get("id")),
        owner_user_id=_parse_int(row.get("owner_user_id")),
        owner_group_id=_parse_int(row.get("owner_group_id")),
        mode=_parse_int(row.get("mode")) or 0,
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
        status=str(row.get("status", "active")),
        source_idea_id=_parse_id_value(row.get("source_idea_id")),
        name=str(row.get("name", "")),
        cadence=str(row.get("cadence", "daily")),
        target_count=int(row.get("target_count", 1)),
        streak_count=int(row.get("streak_count", 0)),
        active=bool(row.get("active", True)),
        last_completed_on=_parse_date_or_none(row.get("last_completed_on")),
        completion_timestamps=_parse_datetime_list(row.get("completion_timestamps")),
        tags=_parse_string_tuple(row.get("tags")),
    )


def _row_to_event(row: dict[str, Any]) -> CalendarEvent:
    return CalendarEvent(
        id=_parse_int(row.get("id")),
        owner_user_id=_parse_int(row.get("owner_user_id")),
        owner_group_id=_parse_int(row.get("owner_group_id")),
        mode=_parse_int(row.get("mode")) or 0,
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
        status=str(row.get("status", "active")),
        source_idea_id=_parse_id_value(row.get("source_idea_id")),
        title=str(row.get("title", "")),
        start_at=_parse_datetime_or_none(row.get("start_at")),
        end_at=_parse_datetime_or_none(row.get("end_at")),
        description=str(row.get("description", "")),
        location=str(row.get("location", "")),
        all_day=bool(row.get("all_day", False)),
        attendee_ids=_parse_id_tuple(row.get("attendee_ids")),
        tags=_parse_string_tuple(row.get("tags")),
    )


def _parse_id_value(value: Any) -> str | int | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    return text


def _parse_id_tuple(value: Any) -> tuple[str | int, ...]:
    items = _parse_json_list(value)
    return tuple(_parse_id_value(item) for item in items if _parse_id_value(item) is not None)


def _parse_string_tuple(value: Any) -> tuple[str, ...]:
    return tuple(item for item in _parse_json_list(value) if item)


def _parse_json_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if value in (None, ""):
        return utc_now()
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _parse_datetime_or_none(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return _parse_datetime(value)


def _parse_date_or_none(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))


def _parse_datetime_list(value: Any) -> list[datetime]:
    items = _parse_json_list(value)
    parsed: list[datetime] = []
    for item in items:
        if item in (None, ""):
            continue
        if isinstance(item, datetime):
            parsed.append(item if item.tzinfo is not None else item.replace(tzinfo=timezone.utc))
            continue
        parsed.append(_parse_datetime(item))
    return parsed


def _parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
