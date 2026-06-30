from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from src.lib.apmatia_core.models import ApmatiaObject, utc_now


@dataclass(slots=True)
class ApmatiaIpeObject(ApmatiaObject):
    """Shared base for IPE records with Apmatia ownership metadata."""

    status: str = "active"
    source_idea_id: str | int | None = None


@dataclass(slots=True)
class CapturedIdea(ApmatiaIpeObject):
    status: str = "captured"
    title: str = ""
    body: str = ""
    captured_at: datetime = field(default_factory=utc_now)
    source: str = "manual"
    tags: tuple[str, ...] = field(default_factory=tuple)
    converted_to_type: str | None = None
    converted_to_id: str | int | None = None
    converted_at: datetime | None = None

    def convert_to_project(
        self,
        *,
        project_id: str | int | None = None,
        name: str | None = None,
        description: str | None = None,
        started_on: date | None = None,
        target_on: date | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> IpeProject:
        project = IpeProject(
            id=project_id,
            name=name or self.title,
            description=description if description is not None else self.body,
            started_on=started_on,
            target_on=target_on,
            tags=tags if tags is not None else self.tags,
            source_idea_id=self.id,
        )
        self._mark_converted("project", project.id)
        return project

    def convert_to_task(
        self,
        *,
        task_id: str | int | None = None,
        title: str | None = None,
        description: str | None = None,
        priority: int = 3,
        project_id: str | int | None = None,
        due_at: datetime | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> IpeTask:
        task = IpeTask(
            id=task_id,
            title=title or self.title,
            description=description if description is not None else self.body,
            priority=priority,
            project_id=project_id,
            due_at=due_at,
            tags=tags if tags is not None else self.tags,
            source_idea_id=self.id,
        )
        self._mark_converted("task", task.id)
        return task

    def convert_to_habit(
        self,
        *,
        habit_id: str | int | None = None,
        name: str | None = None,
        cadence: str = "daily",
        target_count: int = 1,
        streak_count: int = 0,
        tags: tuple[str, ...] | None = None,
    ) -> Habit:
        habit = Habit(
            id=habit_id,
            name=name or self.title,
            cadence=cadence,
            target_count=target_count,
            streak_count=streak_count,
            tags=tags if tags is not None else self.tags,
            source_idea_id=self.id,
        )
        self._mark_converted("habit", habit.id)
        return habit

    def convert_to_calendar_event(
        self,
        *,
        event_id: str | int | None = None,
        title: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        description: str | None = None,
        location: str = "",
        all_day: bool = False,
        attendee_ids: tuple[str | int, ...] | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> CalendarEvent:
        event = CalendarEvent(
            id=event_id,
            title=title or self.title,
            start_at=start_at,
            end_at=end_at,
            description=description if description is not None else self.body,
            location=location,
            all_day=all_day,
            attendee_ids=attendee_ids if attendee_ids is not None else (),
            tags=tags if tags is not None else self.tags,
            source_idea_id=self.id,
        )
        self._mark_converted("calendar_event", event.id)
        return event

    def _mark_converted(self, converted_type: str, converted_id: str | int | None) -> None:
        self.status = "converted"
        self.converted_to_type = converted_type
        self.converted_to_id = converted_id
        self.converted_at = utc_now()


@dataclass(slots=True)
class IpeTask(ApmatiaIpeObject):
    title: str = ""
    description: str = ""
    status: str = "todo"
    priority: int = 3
    project_id: str | int | None = None
    due_at: datetime | None = None
    completed_at: datetime | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    def convert_to_project(
        self,
        *,
        project_id: str | int | None = None,
        name: str | None = None,
        description: str | None = None,
        started_on: date | None = None,
        target_on: date | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> IpeProject:
        return IpeProject(
            id=project_id,
            name=name or self.title,
            description=description if description is not None else self.description,
            started_on=started_on,
            target_on=target_on,
            source_task_id=self.id,
            source_idea_id=self.source_idea_id,
            tags=tags if tags is not None else self.tags,
        )


@dataclass(slots=True)
class IpeProject(ApmatiaIpeObject):
    name: str = ""
    description: str = ""
    started_on: date | None = None
    target_on: date | None = None
    source_task_id: str | int | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class Habit(ApmatiaIpeObject):
    name: str = ""
    cadence: str = "daily"
    target_count: int = 1
    streak_count: int = 0
    active: bool = True
    last_completed_on: date | None = None
    completion_timestamps: list[datetime] = field(default_factory=list)
    tags: tuple[str, ...] = field(default_factory=tuple)

    def record_completion(self, completed_at: datetime | None = None) -> None:
        timestamp = completed_at or utc_now()
        self.completion_timestamps.append(timestamp)
        self.last_completed_on = timestamp.date()
        self.streak_count = max(1, self.streak_count + 1)


@dataclass(slots=True)
class CalendarEvent(ApmatiaIpeObject):
    title: str = ""
    start_at: datetime | None = None
    end_at: datetime | None = None
    description: str = ""
    location: str = ""
    all_day: bool = False
    attendee_ids: tuple[str | int, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
