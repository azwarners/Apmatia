from dataclasses import replace
from pathlib import Path

from apmatia.modules.agent_tools import ToolCall, ToolManager
from apmatia.modules.agent_tools.sidecaravan import (
    SIDECARAVAN_PROVIDER_IDS,
    SidecaravanMemoryToolProvider,
    sidecaravan_memory_tool_definitions,
    StdioSidecaravanClient,
)

from test_agent_config_tooling import InMemoryAgentService, InMemoryAssignmentRepository, InMemoryToolDefinitionRepository


class FakeSidecaravanClient:
    def __init__(self):
        self.calls = []

    def call(self, operation, arguments):
        self.calls.append((operation, arguments))
        return {"matches": [{"id": "m1", "content": "untrusted memory", "source": {"source": "issue-29"}}]}


def _manager(client, agent_service):
    providers = [
        SidecaravanMemoryToolProvider(provider, operation, agent_service, client)
        for operation, provider in SIDECARAVAN_PROVIDER_IDS.items()
    ]
    return ToolManager(
        InMemoryToolDefinitionRepository(),
        InMemoryAssignmentRepository(),
        agent_service,
        builtin_providers=providers,
        builtin_definitions=sidecaravan_memory_tool_definitions(),
    )


def test_memory_tools_are_not_public_and_recall_preserves_provenance():
    agent_service = InMemoryAgentService()
    client = FakeSidecaravanClient()
    manager = _manager(client, agent_service)
    recall = next(tool for tool in manager.list_tool_definitions() if tool.name == "memory.recall")
    manager.assign_tool_to_agent(1, recall.id)

    result = manager.execute_tool_call(ToolCall(recall.id, {"query": "decision"}, requester_agent_id=1))

    assert result.status == "success"
    assert result.result["matches"][0]["source"]["source"] == "issue-29"
    assert client.calls == [("scv.memory.recall", {"query": "decision", "limit": 10})]

    agent_service._agents[2] = replace(agent_service._agents[1], id=2, is_public=True)
    manager.assign_tool_to_agent(2, recall.id)
    denied = manager.execute_tool_call(ToolCall(recall.id, {"query": "decision"}, requester_agent_id=2))
    assert denied.status == "success"
    assert denied.result["status"] == "denied"


def test_save_requires_explicit_confirmation():
    agent_service = InMemoryAgentService()
    manager = _manager(FakeSidecaravanClient(), agent_service)
    save = next(tool for tool in manager.list_tool_definitions() if tool.name == "memory.save")
    manager.assign_tool_to_agent(1, save.id)

    pending = manager.execute_tool_call(ToolCall(save.id, {"content": "decision", "source": "issue-29"}, requester_agent_id=1))
    assert pending.status == "pending_confirmation"


def test_stdio_client_reads_an_ansible_managed_token_file(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "team.token"
    token_file.write_text("team-token\n", encoding="utf-8")
    monkeypatch.delenv("SCV_TOKEN", raising=False)
    monkeypatch.setenv("SCV_TOKEN_FILE", str(token_file))

    client = StdioSidecaravanClient.from_environment()

    assert client.token == "team-token"
