"""Unit tests for tool management orchestration and execution."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from src.lib.agent_management.models import Agent
from src.lib.agent_management.services import AgentService
from src.lib.memory_management.models import MemoryItem
from src.lib.memory_management.module import MemoryManager
from src.lib.memory_management.repositories import MemoryRepository
from src.lib.memory_management.tooling import build_memory_tool_providers, memory_tool_definitions
from src.lib.tool_management.models import ToolCall
from src.lib.tool_management.module import ToolManager
from src.lib.tool_management.repositories import AgentToolAssignmentRepository, ToolDefinitionRepository
from src.lib.system_audit.tooling import build_system_audit_tool_providers, system_audit_tool_definitions
from src.lib.wiki_management.module import WikiManager
from src.lib.wiki_management.repositories import WikiNodeRepository, WikiRepository
from src.lib.wiki_management.tooling import build_wiki_tool_providers, wiki_tool_definitions


class InMemoryToolDefinitionRepository(ToolDefinitionRepository):
    def __init__(self):
        self._tools = {}
        self._next_id = 1

    def create(self, tool):
        tool_id = self._next_id
        self._next_id += 1
        self._tools[tool_id] = replace(tool, id=tool_id)
        return tool_id

    def get(self, tool_id):
        return self._tools.get(tool_id)

    def get_by_name(self, name):
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None

    def get_by_provider_id(self, provider_id):
        for tool in self._tools.values():
            if tool.provider_id == provider_id:
                return tool
        return None

    def list_all(self):
        return list(self._tools.values())

    def update(self, tool):
        self._tools[tool.id] = tool


class InMemoryAssignmentRepository(AgentToolAssignmentRepository):
    def __init__(self):
        self._assignments = {}
        self._next_id = 1

    def upsert(self, assignment):
        key = (assignment.agent_id, assignment.tool_id)
        existing = self._assignments.get(key)
        if existing is None:
            assignment = replace(assignment, id=self._next_id)
            self._next_id += 1
        else:
            assignment = replace(assignment, id=existing.id)
        self._assignments[key] = assignment
        return assignment

    def get(self, assignment_id):
        for assignment in self._assignments.values():
            if assignment.id == assignment_id:
                return assignment
        return None

    def get_by_agent_tool(self, agent_id, tool_id):
        return self._assignments.get((agent_id, tool_id))

    def list_by_agent(self, agent_id):
        return [assignment for (stored_agent_id, _), assignment in self._assignments.items() if stored_agent_id == agent_id]

    def delete(self, agent_id, tool_id):
        return self._assignments.pop((agent_id, tool_id), None) is not None


class InMemoryAgentService(AgentService):
    def __init__(self):
        self._agents = {1: Agent(id=1, name="Agent One", owner_user_id=1)}

    def create_agent(self, name: str, **kwargs):
        raise NotImplementedError

    def update_agent(self, agent_id: int, **updates):
        agent = self._agents[agent_id]
        updated = replace(agent, **updates)
        self._agents[agent_id] = updated
        return updated

    def delete_agent(self, agent_id: int):
        raise NotImplementedError

    def get_agent(self, agent_id: int):
        return self._agents.get(agent_id)

    def list_agents(self):
        return list(self._agents.values())


class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self):
        self._memories = {}
        self._next_id = 1

    def create(self, memory: MemoryItem) -> int:
        memory_id = self._next_id
        self._next_id += 1
        self._memories[memory_id] = replace(memory, id=memory_id)
        return memory_id

    def get(self, memory_id: int):
        return self._memories.get(memory_id)

    def list_all(self):
        return list(self._memories.values())

    def search(self, query: str, **kwargs):
        text = query.lower().strip()
        if not text:
            return self.list_all()
        return [
            memory
            for memory in self._memories.values()
            if text in memory.title.lower() or text in memory.content.lower()
        ]

    def update(self, memory: MemoryItem) -> None:
        self._memories[int(memory.id)] = memory


class InMemoryWikiRepository(WikiRepository):
    def __init__(self):
        self._wikis = {}

    def create(self, wiki):
        self._wikis[wiki.wiki_id] = wiki
        return wiki.wiki_id

    def get(self, wiki_id):
        return self._wikis.get(wiki_id)

    def list_all(self):
        return list(self._wikis.values())

    def update(self, wiki):
        self._wikis[wiki.wiki_id] = wiki

    def delete(self, wiki_id):
        return self._wikis.pop(wiki_id, None) is not None


class InMemoryWikiNodeRepository(WikiNodeRepository):
    def __init__(self):
        self._nodes = {}

    def create(self, node):
        self._nodes[node.node_id] = node
        return node.node_id

    def get(self, node_id):
        return self._nodes.get(node_id)

    def list_by_wiki(self, wiki_id):
        return [node for node in self._nodes.values() if node.wiki_id == wiki_id]

    def update(self, node):
        self._nodes[node.node_id] = node

    def delete(self, node_id):
        return self._nodes.pop(node_id, None) is not None


@pytest.fixture
def tool_manager():
    return ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        InMemoryAgentService(),
    )


def test_builtin_tools_are_seeded(tool_manager):
    names = {tool.name for tool in tool_manager.list_tool_definitions()}
    assert {"echo", "get_current_time"} <= names


def test_memory_and_wiki_builtin_tools_are_seeded():
    agent_service = InMemoryAgentService()
    tool_manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=[
            *build_memory_tool_providers(MemoryManager(InMemoryMemoryRepository()), agent_service),
            *build_wiki_tool_providers(WikiManager(InMemoryWikiRepository(), InMemoryWikiNodeRepository()), agent_service),
        ],
        builtin_definitions=[*memory_tool_definitions(), *wiki_tool_definitions()],
    )

    names = {tool.name for tool in tool_manager.list_tool_definitions()}

    assert {
        "memory_create",
        "memory_search",
        "wiki_create_branch",
        "wiki_create_leaf",
        "wiki_update_node",
        "wiki_get_tree",
        "wiki_search",
        "wiki_move_node",
        "wiki_reorder_node",
    } <= names


def test_disabled_tool_cannot_execute(tool_manager):
    echo_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "echo")
    tool_manager.assign_tool_to_agent(1, echo_tool.id)
    tool_manager.update_tool_definition(echo_tool.id, enabled=False)

    result = tool_manager.execute_tool_call(
        ToolCall(tool_id=echo_tool.id, requester_agent_id=1, arguments={"text": "hello"})
    )

    assert result.status == "denied"
    assert result.result is None


def test_unassigned_tool_cannot_execute(tool_manager):
    echo_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "echo")

    result = tool_manager.execute_tool_call(
        ToolCall(tool_id=echo_tool.id, requester_agent_id=1, arguments={"text": "hello"})
    )

    assert result.status == "denied"


def test_assigned_enabled_tool_executes(tool_manager):
    echo_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "echo")
    tool_manager.assign_tool_to_agent(1, echo_tool.id)

    result = tool_manager.execute_tool_call(
        ToolCall(tool_id=echo_tool.id, requester_agent_id=1, arguments={"text": "hello"})
    )

    assert result.status == "success"
    assert result.result == {"text": "hello"}
    assert result.metadata["tool_id"] == echo_tool.id


def test_input_schema_validation_rejects_bad_arguments(tool_manager):
    echo_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "echo")
    tool_manager.assign_tool_to_agent(1, echo_tool.id)

    result = tool_manager.execute_tool_call(
        ToolCall(tool_id=echo_tool.id, requester_agent_id=1, arguments={"text": 123})
    )

    assert result.status == "invalid_arguments"
    assert result.result is None
    assert result.metadata["validation_errors"]


def test_confirmation_required_tool_returns_pending(tool_manager):
    echo_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "echo")
    tool_manager.assign_tool_to_agent(1, echo_tool.id, confirmation_required=True)

    result = tool_manager.execute_tool_call(
        ToolCall(tool_id=echo_tool.id, requester_agent_id=1, arguments={"text": "hello"})
    )

    assert result.status == "pending_confirmation"
    assert result.result is None


def test_get_current_time_returns_structured_result(tool_manager):
    time_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "get_current_time")
    tool_manager.assign_tool_to_agent(1, time_tool.id)

    result = tool_manager.execute_tool_call(
        ToolCall(tool_id=time_tool.id, requester_agent_id=1, arguments={})
    )

    assert result.status == "success"
    assert isinstance(result.result, dict)
    assert isinstance(result.result["current_time"], str)


def test_system_audit_command_executes_with_allowlist():
    agent_service = InMemoryAgentService()
    tool_manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_system_audit_tool_providers(agent_service),
        builtin_definitions=system_audit_tool_definitions(),
    )

    audit_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "apmatia_system_audit")
    tool_manager.assign_tool_to_agent(1, audit_tool.id)

    fake_completed = SimpleNamespace(returncode=0, stdout="Linux test\n", stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.lib.system_audit.tooling.shutil.which", lambda command: f"/bin/{command}")
        monkeypatch.setattr("src.lib.system_audit.tooling.subprocess.run", lambda *args, **kwargs: fake_completed)
        result = tool_manager.execute_tool_call(
            ToolCall(
                tool_id=audit_tool.id,
                requester_agent_id=1,
                arguments={"command": "uname", "args": ["-a"]},
            )
        )

    assert result.status == "success"
    assert result.result["command"] == "uname"
    assert result.result["args"] == ["-a"]
    assert result.result["stdout"] == "Linux test\n"
    assert result.result["returncode"] == 0


def test_memory_create_and_search_tool_execute():
    agent_service = InMemoryAgentService()
    tool_manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_memory_tool_providers(MemoryManager(InMemoryMemoryRepository()), agent_service),
        builtin_definitions=memory_tool_definitions(),
    )

    create_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_create")
    search_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_search")
    tool_manager.assign_tool_to_agent(1, create_tool.id)
    tool_manager.assign_tool_to_agent(1, search_tool.id)

    created = tool_manager.execute_tool_call(
        ToolCall(
            tool_id=create_tool.id,
            requester_agent_id=1,
            discussion_id="disc-9",
            arguments={"title": "Trip note", "content": "Bring passport", "tags": ["travel"]},
        )
    )
    searched = tool_manager.execute_tool_call(
        ToolCall(
            tool_id=search_tool.id,
            requester_agent_id=1,
            arguments={"query": "passport"},
        )
    )

    assert created.status == "success"
    assert created.result["memory_id"] > 0
    assert created.result["owner_agent_id"] == 1
    assert searched.status == "success"
    assert searched.result["count"] == 1
    assert searched.result["memories"][0]["title"] == "Trip note"
    assert searched.result["memories"][0]["owner_agent_id"] == 1


def test_memory_tools_are_scoped_to_each_calling_agent():
    agent_service = InMemoryAgentService()
    agent_service._agents[2] = Agent(id=2, name="Agent Two", owner_user_id=1)
    memory_repo = InMemoryMemoryRepository()
    tool_manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_memory_tool_providers(MemoryManager(memory_repo), agent_service),
        builtin_definitions=memory_tool_definitions(),
    )

    create_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_create")
    search_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_search")
    get_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_get")
    for agent_id in (1, 2):
        tool_manager.assign_tool_to_agent(agent_id, create_tool.id)
        tool_manager.assign_tool_to_agent(agent_id, search_tool.id)
        tool_manager.assign_tool_to_agent(agent_id, get_tool.id)

    created_one = tool_manager.execute_tool_call(
        ToolCall(
            tool_id=create_tool.id,
            requester_agent_id=1,
            arguments={"title": "Agent One note", "content": "One only"},
        )
    )
    created_two = tool_manager.execute_tool_call(
        ToolCall(
            tool_id=create_tool.id,
            requester_agent_id=2,
            arguments={"title": "Agent Two note", "content": "Two only"},
        )
    )
    search_one = tool_manager.execute_tool_call(
        ToolCall(tool_id=search_tool.id, requester_agent_id=1, arguments={"query": "note"})
    )
    search_two = tool_manager.execute_tool_call(
        ToolCall(tool_id=search_tool.id, requester_agent_id=2, arguments={"query": "note"})
    )
    cross_agent_get = tool_manager.execute_tool_call(
        ToolCall(
            tool_id=get_tool.id,
            requester_agent_id=2,
            arguments={"memory_id": created_one.result["memory_id"]},
        )
    )

    assert created_one.status == "success"
    assert created_two.status == "success"
    assert created_one.result["owner_agent_id"] == 1
    assert created_two.result["owner_agent_id"] == 2
    assert [memory["title"] for memory in search_one.result["memories"]] == ["Agent One note"]
    assert [memory["title"] for memory in search_two.result["memories"]] == ["Agent Two note"]
    assert cross_agent_get.status == "error"
    assert "Memory not found" in str(cross_agent_get.error)


def test_memory_create_does_not_auto_link_discussion():
    agent_service = InMemoryAgentService()
    memory_repo = InMemoryMemoryRepository()
    memory_manager = MemoryManager(memory_repo)
    tool_manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_memory_tool_providers(memory_manager, agent_service),
        builtin_definitions=memory_tool_definitions(),
    )

    create_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_create")
    tool_manager.assign_tool_to_agent(1, create_tool.id)

    created = tool_manager.execute_tool_call(
        ToolCall(
            tool_id=create_tool.id,
            requester_agent_id=1,
            discussion_id="disc-9",
            arguments={"title": "Global note", "content": "Available everywhere"},
        )
    )

    stored_memory = memory_repo.get(created.result["memory_id"])

    assert created.status == "success"
    assert stored_memory is not None
    assert stored_memory.owner_agent_id == 1
    assert stored_memory.source_discussion_id is None


def test_memory_create_tool_errors_when_agent_has_no_owner_user_id():
    agent_service = InMemoryAgentService()
    agent_service._agents[1] = Agent(id=1, name="Agent One", owner_user_id=None)
    tool_manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_memory_tool_providers(MemoryManager(InMemoryMemoryRepository()), agent_service),
        builtin_definitions=memory_tool_definitions(),
    )

    create_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_create")
    tool_manager.assign_tool_to_agent(1, create_tool.id)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "src.lib.discussions.discussion_state._get_discussion",
            lambda discussion_id: None,
        )
        result = tool_manager.execute_tool_call(
            ToolCall(
                tool_id=create_tool.id,
                requester_agent_id=1,
                discussion_id="disc-missing-owner",
                arguments={"title": "Unowned", "content": "Should fail"},
            )
        )

    assert result.status == "error"
    assert "has no owner_user_id" in str(result.error)


def test_memory_tool_repairs_ownerless_agent_from_discussion_owner():
    agent_service = InMemoryAgentService()
    agent_service._agents[1] = Agent(id=1, name="Agent One", owner_user_id=None)
    tool_manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_memory_tool_providers(MemoryManager(InMemoryMemoryRepository()), agent_service),
        builtin_definitions=memory_tool_definitions(),
    )

    create_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_create")
    tool_manager.assign_tool_to_agent(1, create_tool.id)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "src.lib.discussions.discussion_state._get_discussion",
            lambda discussion_id: SimpleNamespace(owner_user_id=77) if discussion_id == "disc-9" else None,
        )
        result = tool_manager.execute_tool_call(
            ToolCall(
                tool_id=create_tool.id,
                requester_agent_id=1,
                discussion_id="disc-9",
                arguments={"title": "Recovered", "content": "Recovered owner"},
            )
        )

    assert result.status == "success"
    assert result.result["title"] == "Recovered"
    assert agent_service.get_agent(1).owner_user_id == 77


def test_wiki_tools_execute_against_focused_discussion_wiki():
    agent_service = InMemoryAgentService()
    wiki_manager = WikiManager(InMemoryWikiRepository(), InMemoryWikiNodeRepository())
    wiki = wiki_manager.create_wiki("Tutor Notes", owner_user_id=1, owner_agent_id=1)
    tool_manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_wiki_tool_providers(wiki_manager, agent_service),
        builtin_definitions=wiki_tool_definitions(),
    )

    create_branch_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "wiki_create_branch")
    create_leaf_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "wiki_create_leaf")
    search_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "wiki_search")
    tree_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "wiki_get_tree")
    tool_manager.assign_tool_to_agent(1, create_branch_tool.id)
    tool_manager.assign_tool_to_agent(1, create_leaf_tool.id)
    tool_manager.assign_tool_to_agent(1, search_tool.id)
    tool_manager.assign_tool_to_agent(1, tree_tool.id)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "src.lib.discussions.discussion_state._get_discussion",
            lambda discussion_id: SimpleNamespace(owner_user_id=1, focused_wiki_id=wiki.wiki_id)
            if discussion_id == "disc-tutor"
            else None,
        )
        branch_result = tool_manager.execute_tool_call(
            ToolCall(
                tool_id=create_branch_tool.id,
                requester_agent_id=1,
                discussion_id="disc-tutor",
                arguments={"parent_id": wiki.root_node_id, "title": "Lesson 1"},
            )
        )
        leaf_result = tool_manager.execute_tool_call(
            ToolCall(
                tool_id=create_leaf_tool.id,
                requester_agent_id=1,
                discussion_id="disc-tutor",
                arguments={
                    "parent_id": branch_result.result["id"],
                    "title": "Key idea",
                    "body": "Isolate the variable before dividing.",
                },
            )
        )
        search_result = tool_manager.execute_tool_call(
            ToolCall(
                tool_id=search_tool.id,
                requester_agent_id=1,
                discussion_id="disc-tutor",
                arguments={"query": "isolate"},
            )
        )
        tree_result = tool_manager.execute_tool_call(
            ToolCall(
                tool_id=tree_tool.id,
                requester_agent_id=1,
                discussion_id="disc-tutor",
                arguments={},
            )
        )

    assert branch_result.status == "success"
    assert branch_result.result["wiki_id"] == wiki.wiki_id
    assert leaf_result.status == "success"
    assert leaf_result.result["body"] == "Isolate the variable before dividing."
    assert search_result.status == "success"
    assert search_result.result["count"] == 1
    assert search_result.result["results"][0]["title"] == "Key idea"
    assert tree_result.status == "success"
    assert tree_result.result["wiki"]["id"] == wiki.wiki_id
    assert tree_result.result["root"]["children"][0]["title"] == "Lesson 1"


def test_wiki_move_update_and_reorder_tools_execute():
    agent_service = InMemoryAgentService()
    wiki_manager = WikiManager(InMemoryWikiRepository(), InMemoryWikiNodeRepository())
    wiki = wiki_manager.create_wiki("Tutor Notes", owner_user_id=1, owner_agent_id=1)
    branch_a = wiki_manager.create_branch(
        wiki.wiki_id,
        wiki.root_node_id,
        "Lesson 1",
        requester_user_id=1,
        requester_group_ids=set(),
    )
    branch_b = wiki_manager.create_branch(
        wiki.wiki_id,
        wiki.root_node_id,
        "Lesson 2",
        requester_user_id=1,
        requester_group_ids=set(),
    )
    leaf = wiki_manager.create_leaf(
        wiki.wiki_id,
        branch_a.node_id,
        "Practice",
        body="Try one equation.",
        requester_user_id=1,
        requester_group_ids=set(),
    )
    tool_manager = ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=build_wiki_tool_providers(wiki_manager, agent_service),
        builtin_definitions=wiki_tool_definitions(),
    )

    update_node_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "wiki_update_node")
    move_node_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "wiki_move_node")
    reorder_node_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "wiki_reorder_node")
    tool_manager.assign_tool_to_agent(1, update_node_tool.id)
    tool_manager.assign_tool_to_agent(1, move_node_tool.id)
    tool_manager.assign_tool_to_agent(1, reorder_node_tool.id)

    updated = tool_manager.execute_tool_call(
        ToolCall(
            tool_id=update_node_tool.id,
            requester_agent_id=1,
            arguments={"node_id": leaf.node_id, "title": "Practice again", "body": "Try two equations."},
        )
    )
    moved = tool_manager.execute_tool_call(
        ToolCall(
            tool_id=move_node_tool.id,
            requester_agent_id=1,
            arguments={"node_id": leaf.node_id, "new_parent_id": branch_b.node_id},
        )
    )
    reordered = tool_manager.execute_tool_call(
        ToolCall(
            tool_id=reorder_node_tool.id,
            requester_agent_id=1,
            arguments={"node_id": leaf.node_id, "new_sort_order": 0},
        )
    )

    assert updated.status == "success"
    assert updated.result["title"] == "Practice again"
    assert updated.result["body"] == "Try two equations."
    assert moved.status == "success"
    assert moved.result["parent_id"] == branch_b.node_id
    assert reordered.status == "success"
    assert reordered.result["sort_order"] == 0
