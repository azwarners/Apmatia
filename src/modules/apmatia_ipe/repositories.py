from __future__ import annotations

from typing import Protocol

from .models import CalendarEvent, CapturedIdea, Habit, IpeProject, IpeTask


class CapturedIdeaRepository(Protocol):
    def create(self, idea: CapturedIdea) -> int:
        raise NotImplementedError

    def get(self, idea_id: int) -> CapturedIdea | None:
        raise NotImplementedError

    def list_all(self) -> list[CapturedIdea]:
        raise NotImplementedError

    def update(self, idea: CapturedIdea) -> None:
        raise NotImplementedError

    def delete(self, idea_id: int) -> bool:
        raise NotImplementedError


class IpeTaskRepository(Protocol):
    def create(self, task: IpeTask) -> int:
        raise NotImplementedError

    def get(self, task_id: int) -> IpeTask | None:
        raise NotImplementedError

    def list_all(self) -> list[IpeTask]:
        raise NotImplementedError

    def update(self, task: IpeTask) -> None:
        raise NotImplementedError

    def delete(self, task_id: int) -> bool:
        raise NotImplementedError


class IpeProjectRepository(Protocol):
    def create(self, project: IpeProject) -> int:
        raise NotImplementedError

    def get(self, project_id: int) -> IpeProject | None:
        raise NotImplementedError

    def list_all(self) -> list[IpeProject]:
        raise NotImplementedError

    def update(self, project: IpeProject) -> None:
        raise NotImplementedError

    def delete(self, project_id: int) -> bool:
        raise NotImplementedError


class HabitRepository(Protocol):
    def create(self, habit: Habit) -> int:
        raise NotImplementedError

    def get(self, habit_id: int) -> Habit | None:
        raise NotImplementedError

    def list_all(self) -> list[Habit]:
        raise NotImplementedError

    def update(self, habit: Habit) -> None:
        raise NotImplementedError

    def delete(self, habit_id: int) -> bool:
        raise NotImplementedError


class CalendarEventRepository(Protocol):
    def create(self, event: CalendarEvent) -> int:
        raise NotImplementedError

    def get(self, event_id: int) -> CalendarEvent | None:
        raise NotImplementedError

    def list_all(self) -> list[CalendarEvent]:
        raise NotImplementedError

    def update(self, event: CalendarEvent) -> None:
        raise NotImplementedError

    def delete(self, event_id: int) -> bool:
        raise NotImplementedError
