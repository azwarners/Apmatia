from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from src.lib.agent_management.models import Agent
from src.modules.apmatia_ipe.models import CalendarEvent, CapturedIdea, Habit, IpeTask
from src.modules.apmatia_ipe.services import ApmatiaIpeService
from src.modules.apmatia_ipe.sqlite_repositories import SQLiteIpeBundle
from src.modules.apmatia_ipe.tools import IpeToolProvider


class FakeAgentService:
    def __init__(self, agents: list[Agent] | None = None):
        self._agents = {int(agent.id): agent for agent in agents or [] if agent.id is not None}
        self.created: list[Agent] = []

    def create_agent(self, name: str, **kwargs) -> Agent:
        agent_id = max(self._agents.keys(), default=0) + 1
        payload = {
            "id": agent_id,
            "name": name,
            "owner_user_id": kwargs.get("owner_user_id"),
            "owner_group_id": kwargs.get("owner_group_id"),
            "mode": kwargs.get("mode", 0),
            "prompt_id": kwargs.get("prompt_id"),
            "system_prompt_id": kwargs.get("system_prompt_id", 0),
            "memory_id": kwargs.get("memory_id", 0),
            "rag_root_ids": list(kwargs.get("rag_root_ids", [])),
            "tool_ids": list(kwargs.get("tool_ids", [])),
            "default_model_id": kwargs.get("default_model_id"),
            "active_model_id": kwargs.get("active_model_id"),
            "metadata": dict(kwargs.get("metadata", {})),
        }
        agent = Agent(**payload)
        self._agents[agent_id] = agent
        self.created.append(agent)
        return agent

    def clone_agent(self, source_agent_id: int, name: str, **kwargs) -> Agent:  # pragma: no cover - not used
        source = self._agents[source_agent_id]
        allowed = {
            key: value
            for key, value in kwargs.items()
            if key in {
                "owner_user_id",
                "owner_group_id",
                "mode",
                "prompt_id",
                "system_prompt_id",
                "memory_id",
                "rag_root_ids",
                "tool_ids",
                "default_model_id",
                "active_model_id",
                "metadata",
            }
        }
        cloned = replace(source, id=max(self._agents.keys(), default=0) + 1, name=name, **allowed)
        self._agents[int(cloned.id)] = cloned
        return cloned

    def update_agent(self, agent_id: int, **updates) -> Agent:
        allowed_updates = {
            key: value
            for key, value in updates.items()
            if key in {
                "owner_user_id",
                "owner_group_id",
                "mode",
                "name",
                "prompt_id",
                "system_prompt_id",
                "memory_id",
                "rag_root_ids",
                "tool_ids",
                "default_model_id",
                "active_model_id",
                "metadata",
            }
        }
        updated = replace(self._agents[agent_id], **allowed_updates)
        self._agents[agent_id] = updated
        return updated

    def delete_agent(self, agent_id: int) -> bool:  # pragma: no cover - not used
        return self._agents.pop(agent_id, None) is not None

    def get_agent(self, agent_id: int) -> Agent | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[Agent]:
        return list(self._agents.values())


def test_ipe_service_converts_idea_to_task_and_deletes_source(tmp_path):
    bundle = SQLiteIpeBundle(tmp_path / "ipe.sqlite")
    service = ApmatiaIpeService(bundle)

    idea = CapturedIdea(id="idea-1", owner_user_id=7, title="Write weekly review", body="Think through the week.")
    bundle.ideas.create(idea)

    task = service.convert_idea_to_task(1, priority=1)

    assert task.id == 1
    assert task.title == "Write weekly review"
    assert task.description == "Think through the week."
    assert task.source_idea_id == "idea-1"
    assert bundle.ideas.list_all() == []
    assert bundle.tasks.get(1) is not None


def test_ipe_service_finds_overdue_habits_and_next_appointment(tmp_path):
    bundle = SQLiteIpeBundle(tmp_path / "ipe.sqlite")
    service = ApmatiaIpeService(bundle)

    bundle.habits.create(
        Habit(
            id="habit-1",
            owner_user_id=7,
            name="Morning planning",
            target_count=1,
            completion_timestamps=[],
        )
    )
    bundle.tasks.create(
        IpeTask(
            id="task-1",
            owner_user_id=7,
            title="Finish draft",
            due_at=datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc),
            priority=1,
        )
    )
    bundle.calendar_events.create(
        CalendarEvent(
            id="event-1",
            owner_user_id=7,
            title="Standup",
            start_at=datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 6, 29, 18, 30, tzinfo=timezone.utc),
        )
    )

    snapshot = service.what_do_i_do(
        owner_user_id=7,
        requester_group_ids=set(),
        as_of=datetime(2026, 6, 29, 9, 0, tzinfo=timezone.utc),
    )

    assert snapshot["current_time"] == datetime(2026, 6, 29, 9, 0, tzinfo=timezone.utc).isoformat()
    assert snapshot["tasks"][0]["title"] == "Finish draft"
    assert snapshot["unfinished_habits"][0]["name"] == "Morning planning"
    assert snapshot["next_appointment"]["title"] == "Standup"
    assert snapshot["suggested_focus"].startswith("Work on the highest-priority task")


def test_habit_completion_history_is_persisted(tmp_path):
    bundle = SQLiteIpeBundle(tmp_path / "ipe.sqlite")
    habit = Habit(
        id="habit-1",
        owner_user_id=7,
        name="Journal",
        completion_timestamps=[datetime(2026, 6, 28, 8, 0, tzinfo=timezone.utc)],
    )
    bundle.habits.create(habit)

    loaded = bundle.habits.get(1)
    assert loaded is not None
    assert len(loaded.completion_timestamps) == 1


def test_coach_agent_seed_is_idempotent(tmp_path):
    bundle = SQLiteIpeBundle(tmp_path / "ipe.sqlite")
    service = ApmatiaIpeService(bundle)
    agent_service = FakeAgentService()

    first = service.ensure_ipe_coach_agent(
        agent_service=agent_service,
        owner_user_id=7,
        agent_name="nick IPE Coach",
        tool_ids=[99],
    )
    second = service.ensure_ipe_coach_agent(
        agent_service=agent_service,
        owner_user_id=7,
        agent_name="nick IPE Coach",
        tool_ids=[99],
    )

    assert first.id == second.id
    assert first.tool_ids == [99]
    assert first.metadata["module"] == "apmatia_ipe"
    assert len(agent_service.created) == 1


def test_ipe_tool_provider_returns_productivity_snapshot(tmp_path):
    bundle = SQLiteIpeBundle(tmp_path / "ipe.sqlite")
    service = ApmatiaIpeService(bundle)
    agent = Agent(id=1, owner_user_id=7, name="nick IPE Coach", metadata={"module": "apmatia_ipe"})
    agent_service = FakeAgentService([agent])

    bundle.tasks.create(
        IpeTask(
            id="task-1",
            owner_user_id=7,
            title="Review roadmap",
            priority=1,
        )
    )

    provider = IpeToolProvider("builtin.ipe_what_do_i_do", "what_do_i_do", service, agent_service)
    result = provider.execute({}, tool_call=type("ToolCallContext", (), {"requester_agent_id": 1, "discussion_id": None})())

    assert result["tasks"][0]["title"] == "Review roadmap"
    assert result["suggested_focus"].startswith("Work on the highest-priority task")
