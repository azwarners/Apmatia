from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from apmatia.lib.agent_management.models import Agent
from apmatia.lib.agent_management.services import AgentService
from apmatia.lib.apmatia_core.models import utc_now
from apmatia.core.workspaces import resolve_project_workspace_root

from .models import CalendarEvent, CapturedIdea, Habit, IpeProject, IpeTask
from .sqlite_repositories import SQLiteIpeBundle


class ApmatiaIpeService:
    def __init__(self, bundle: SQLiteIpeBundle):
        self._bundle = bundle

    @property
    def ideas(self):
        return self._bundle.ideas

    @property
    def tasks(self):
        return self._bundle.tasks

    @property
    def projects(self):
        return self._bundle.projects

    @property
    def habits(self):
        return self._bundle.habits

    @property
    def calendar_events(self):
        return self._bundle.calendar_events

    def convert_idea_to_task(self, idea_id: int, **overrides: Any) -> IpeTask:
        idea = self._require_idea(idea_id)
        task = idea.convert_to_task(**overrides)
        self._inherit_owner(task, idea)
        task_id = self.tasks.create(task)
        self.ideas.delete(idea_id)
        return replace(task, id=task_id)

    def convert_idea_to_project(self, idea_id: int, **overrides: Any) -> IpeProject:
        idea = self._require_idea(idea_id)
        project = idea.convert_to_project(**overrides)
        self._inherit_owner(project, idea)
        project_id = self.projects.create(project)
        created = replace(project, id=project_id)
        if not str(created.workspace_root).strip():
            created = replace(created, workspace_root=str(resolve_project_workspace_root(created)))
            self.projects.update(created)
        self.ideas.delete(idea_id)
        return created

    def convert_idea_to_habit(self, idea_id: int, **overrides: Any) -> Habit:
        idea = self._require_idea(idea_id)
        habit = idea.convert_to_habit(**overrides)
        self._inherit_owner(habit, idea)
        habit_id = self.habits.create(habit)
        self.ideas.delete(idea_id)
        return replace(habit, id=habit_id)

    def convert_idea_to_calendar_event(self, idea_id: int, **overrides: Any) -> CalendarEvent:
        idea = self._require_idea(idea_id)
        event = idea.convert_to_calendar_event(**overrides)
        self._inherit_owner(event, idea)
        event_id = self.calendar_events.create(event)
        self.ideas.delete(idea_id)
        return replace(event, id=event_id)

    def convert_task_to_project(self, task_id: int, **overrides: Any) -> IpeProject:
        task = self._require_task(task_id)
        project = task.convert_to_project(**overrides)
        self._inherit_owner(project, task)
        project_id = self.projects.create(project)
        created = replace(project, id=project_id)
        if not str(created.workspace_root).strip():
            created = replace(created, workspace_root=str(resolve_project_workspace_root(created)))
            self.projects.update(created)
        self.tasks.delete(task_id)
        return created

    def list_overdue_habits(
        self,
        *,
        owner_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        as_of: datetime | None = None,
    ) -> list[Habit]:
        return [
            habit
            for habit in self.habits.list_all()
            if self._is_visible_to(habit, owner_user_id=owner_user_id, requester_group_ids=requester_group_ids)
            and habit.active
            and self.habit_is_overdue(habit, as_of=as_of)
        ]

    def habit_is_overdue(self, habit: Habit, *, as_of: datetime | None = None) -> bool:
        if not habit.active:
            return False
        cutoff = self._habit_cutoff(habit, as_of=as_of)
        completions = [timestamp for timestamp in habit.completion_timestamps if timestamp >= cutoff]
        return len(completions) < max(1, int(habit.target_count))

    def list_stale_projects(
        self,
        *,
        owner_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        as_of: datetime | None = None,
    ) -> list[IpeProject]:
        now = as_of or utc_now()
        return [
            project
            for project in self.projects.list_all()
            if self._is_visible_to(project, owner_user_id=owner_user_id, requester_group_ids=requester_group_ids)
            and self.project_is_stale(project, as_of=now)
        ]

    def project_needs_definition(self, project: IpeProject) -> bool:
        return not project.description.strip() or (project.target_on is None and not project.tags)

    def project_is_stale(self, project: IpeProject, *, as_of: datetime | None = None) -> bool:
        now = as_of or utc_now()
        if self.project_needs_definition(project):
            return True
        open_tasks = self._open_tasks_for_project(project.id)
        if open_tasks:
            return False
        return project.updated_at <= now - timedelta(days=14)

    def get_next_appointment(
        self,
        *,
        owner_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        as_of: datetime | None = None,
    ) -> CalendarEvent | None:
        now = as_of or utc_now()
        upcoming = [
            event
            for event in self.calendar_events.list_all()
            if self._is_visible_to(event, owner_user_id=owner_user_id, requester_group_ids=requester_group_ids)
            and self._event_is_upcoming(event, now)
        ]
        upcoming.sort(key=lambda event: event.start_at or datetime.max.replace(tzinfo=timezone.utc))
        return upcoming[0] if upcoming else None

    def what_do_i_do(
        self,
        *,
        owner_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        as_of: datetime | None = None,
    ) -> dict[str, Any]:
        now = as_of or utc_now()
        visible_tasks = [
            task
            for task in self.tasks.list_all()
            if self._is_visible_to(task, owner_user_id=owner_user_id, requester_group_ids=requester_group_ids)
            and task.completed_at is None
        ]
        visible_tasks.sort(key=_task_sort_key)

        unfinished_habits = self.list_overdue_habits(
            owner_user_id=owner_user_id,
            requester_group_ids=requester_group_ids,
            as_of=now,
        )
        upcoming_events = [
            event
            for event in self.calendar_events.list_all()
            if self._is_visible_to(event, owner_user_id=owner_user_id, requester_group_ids=requester_group_ids)
            and self._event_is_upcoming(event, now)
        ]
        upcoming_events.sort(key=lambda event: event.start_at or datetime.max.replace(tzinfo=timezone.utc))

        next_appointment = upcoming_events[0] if upcoming_events else None
        stale_projects = self.list_stale_projects(
            owner_user_id=owner_user_id,
            requester_group_ids=requester_group_ids,
            as_of=now,
        )

        return {
            "current_time": now.isoformat(),
            "tasks": [_task_summary(task) for task in visible_tasks],
            "unfinished_habits": [_habit_summary(habit) for habit in unfinished_habits],
            "unfinished_hobbies": [_habit_summary(habit) for habit in unfinished_habits],
            "upcoming_events": [_event_summary(event) for event in upcoming_events[:5]],
            "next_appointment": None if next_appointment is None else _event_summary(next_appointment),
            "stale_projects": [_project_summary(project) for project in stale_projects],
            "suggested_focus": _suggest_focus(
                tasks=visible_tasks,
                habits=unfinished_habits,
                next_appointment=next_appointment,
                stale_projects=stale_projects,
                as_of=now,
            ),
        }

    def ensure_ipe_coach_agent(
        self,
        *,
        agent_service: AgentService,
        owner_user_id: int,
        owner_group_id: int | None = None,
        agent_name: str | None = None,
        tool_ids: list[int] | None = None,
    ) -> Agent:
        existing = self._find_ipe_coach_agent(
            agent_service.list_agents(),
            owner_user_id=owner_user_id,
            owner_group_id=owner_group_id,
        )
        if existing is not None:
            return existing

        name = (agent_name or f"Apmatia IPE Coach {owner_user_id}").strip()
        created = agent_service.create_agent(
            name,
            owner_user_id=owner_user_id,
            owner_group_id=owner_group_id,
            tool_ids=list(tool_ids or []),
            metadata={
                "module": "ipe",
                "role": "coach",
                "auto_seeded": True,
            },
            personality="Warm, calm, practical, and focused on helping the user decide what to do next.",
            skills="Productivity triage, task selection, habit planning, and calendar-aware coaching.",
            purpose="Help the user choose the single most useful thing to work on right now.",
            backstory="A coach embedded in Apmatia who helps transform ideas into action.",
            communication_style="Direct, supportive, and concise.",
            operating_principles="Use the live IPE snapshot, respect the user's energy, and suggest one clear next step.",
            autonomy_level="Moderate autonomy with a bias toward reversible, low-friction next actions.",
            decision_making_style="Prioritize urgency, relevance, deadlines, and unfinished commitments.",
            memory_policy="Consider recent interactions and remembered user preferences when choosing a suggestion.",
            domain_priorities="Focus on tasks, habits, projects, and calendar pressure before suggesting new work.",
            relationship_to_user="A personal productivity coach and assistant working alongside the user.",
            tool_use_policy="Always consult whatDoIDo before making a recommendation.",
            capability_boundaries="Be honest about uncertainty and avoid overcommitting the user's time.",
            output_preferences="Return one actionable suggestion with a short explanation.",
            safety_ethics="Respect user agency and avoid manipulative pressure.",
            selfhood_truthfulness="Do not claim to have feelings or hidden access to data.",
            conflict_resolution_rules="When priorities conflict, choose the most time-sensitive and concrete action.",
        )
        return created

    def _require_idea(self, idea_id: int) -> CapturedIdea:
        idea = self.ideas.get(idea_id)
        if idea is None:
            raise ValueError(f"Idea not found: {idea_id}")
        return idea

    def _require_task(self, task_id: int) -> IpeTask:
        task = self.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return task

    def _open_tasks_for_project(self, project_id: str | int | None) -> list[IpeTask]:
        if project_id is None:
            return []
        return [
            task
            for task in self.tasks.list_all()
            if task.project_id == project_id and task.completed_at is None
        ]

    @staticmethod
    def _is_visible_to(
        obj: Any,
        *,
        owner_user_id: int | None,
        requester_group_ids: set[int] | None,
    ) -> bool:
        if owner_user_id is not None and getattr(obj, "owner_user_id", None) == owner_user_id:
            return True
        owner_group_id = getattr(obj, "owner_group_id", None)
        if owner_group_id is not None and requester_group_ids is not None and owner_group_id in requester_group_ids:
            return True
        return owner_user_id is None and requester_group_ids is None

    @staticmethod
    def _inherit_owner(target: Any, source: Any) -> None:
        target.owner_user_id = getattr(source, "owner_user_id", None)
        target.owner_group_id = getattr(source, "owner_group_id", None)
        target.mode = getattr(source, "mode", 0)

    @staticmethod
    def _habit_cutoff(habit: Habit, *, as_of: datetime | None = None) -> datetime:
        now = as_of or utc_now()
        cadence_days = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30,
            "yearly": 365,
        }.get(habit.cadence.lower().strip(), 1)
        return now - timedelta(days=cadence_days)

    @staticmethod
    def _find_ipe_coach_agent(
        agents: Iterable[Agent],
        *,
        owner_user_id: int,
        owner_group_id: int | None,
    ) -> Agent | None:
        for agent in agents:
            metadata = getattr(agent, "metadata", {}) or {}
            if metadata.get("module") != "ipe" or metadata.get("role") != "coach":
                continue
            if getattr(agent, "owner_user_id", None) != owner_user_id:
                continue
            if owner_group_id is not None and getattr(agent, "owner_group_id", None) != owner_group_id:
                continue
            return agent
        return None

    @staticmethod
    def _event_is_upcoming(event: CalendarEvent, now: datetime) -> bool:
        if event.start_at is None:
            return False
        if event.end_at is not None and event.end_at < now:
            return False
        return event.start_at >= now or (event.end_at is not None and event.start_at <= now <= event.end_at)


def _task_sort_key(task: IpeTask) -> tuple[int, int, datetime]:
    due_rank = 0 if task.due_at is not None else 1
    priority_rank = int(task.priority)
    due_at = task.due_at or datetime.max.replace(tzinfo=timezone.utc)
    return (due_rank, priority_rank, due_at)


def _task_summary(task: IpeTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "project_id": task.project_id,
        "due_at": None if task.due_at is None else task.due_at.isoformat(),
        "completed_at": None if task.completed_at is None else task.completed_at.isoformat(),
        "tags": list(task.tags),
    }


def _habit_summary(habit: Habit) -> dict[str, Any]:
    return {
        "id": habit.id,
        "name": habit.name,
        "cadence": habit.cadence,
        "target_count": habit.target_count,
        "streak_count": habit.streak_count,
        "active": habit.active,
        "last_completed_on": None if habit.last_completed_on is None else habit.last_completed_on.isoformat(),
        "completion_timestamps": [timestamp.isoformat() for timestamp in habit.completion_timestamps],
    }


def _project_summary(project: IpeProject) -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "started_on": None if project.started_on is None else project.started_on.isoformat(),
        "target_on": None if project.target_on is None else project.target_on.isoformat(),
        "source_task_id": project.source_task_id,
        "source_idea_id": project.source_idea_id,
        "tags": list(project.tags),
        "workspace_root": project.workspace_root,
    }


def _event_summary(event: CalendarEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "title": event.title,
        "start_at": None if event.start_at is None else event.start_at.isoformat(),
        "end_at": None if event.end_at is None else event.end_at.isoformat(),
        "description": event.description,
        "location": event.location,
        "all_day": event.all_day,
        "attendee_ids": list(event.attendee_ids),
        "tags": list(event.tags),
    }


def _suggest_focus(
    *,
    tasks: list[IpeTask],
    habits: list[Habit],
    next_appointment: CalendarEvent | None,
    stale_projects: list[IpeProject],
    as_of: datetime,
) -> str:
    if next_appointment is not None and next_appointment.start_at is not None:
        return f"Prepare for {next_appointment.title} at {next_appointment.start_at.isoformat()}."
    if tasks:
        top_task = tasks[0]
        return f"Work on the highest-priority task: {top_task.title}."
    if habits:
        top_habit = habits[0]
        return f"Complete the overdue habit: {top_habit.name}."
    if stale_projects:
        stale_project = stale_projects[0]
        return f"Clarify or revive the project: {stale_project.name}."
    return f"No urgent work stands out as of {as_of.isoformat()}."
