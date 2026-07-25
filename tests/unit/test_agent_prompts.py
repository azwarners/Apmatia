import tempfile

from apmatia.modules.agents.agent_prompt import AgentPrompt, compile_agent_system_prompt, default_agent_prompt
from apmatia.modules.agents.prompt_repositories import (
    AgentPromptManagementTables,
    SQLiteAgentPromptRepository,
)


def _store(path):
    try:
        from persistence import SQLiteStore
    except ModuleNotFoundError:
        from apmatia.lib.persistence.persistence import SQLiteStore
    return SQLiteStore(path)


def test_agent_prompt_defaults():
    prompt = default_agent_prompt()
    assert prompt.personality
    assert prompt.use_raw_prompt_override is False
    assert prompt.raw_prompt_override == ""


def test_compile_agent_system_prompt():
    prompt = AgentPrompt(personality="Warm and direct.", purpose="Help.")
    compiled = compile_agent_system_prompt("Helper", prompt)
    assert "You are Helper." in compiled
    assert "Purpose: Help." in compiled
    assert "Personality: Warm and direct." in compiled


def test_compile_agent_system_prompt_override():
    prompt = AgentPrompt(use_raw_prompt_override=True, raw_prompt_override="  raw prompt  ")
    assert compile_agent_system_prompt("Helper", prompt) == "raw prompt"


def test_prompt_repository_create_get_update():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        store = _store(handle.name)
        repo = SQLiteAgentPromptRepository(store, AgentPromptManagementTables())
        prompt_id = repo.create(AgentPrompt(personality="One"))
        loaded = repo.get(prompt_id)
        assert loaded is not None
        assert loaded.personality == "One"
        repo.update(prompt_id, AgentPrompt(personality="Two"))
        updated = repo.get(prompt_id)
        assert updated is not None
        assert updated.personality == "Two"
