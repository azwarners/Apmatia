from __future__ import annotations

from apmatia.lib.model_management.models import LLM
from apmatia.modules.agent_loops.models import AgentLoopTask, ModelRequest
from apmatia.modules.agent_loops.service import YsparrModelExecutor, _limit_agent_loop_response_size


def test_agent_loop_response_size_is_capped_for_turns():
    config = LLM(id=1, user_alias="Test", backend="openai_compatible", max_response_size=8192)

    limited = _limit_agent_loop_response_size(config)

    assert limited is not None
    assert limited.max_response_size == 1024


def test_agent_loop_system_prompt_pushes_short_turns():
    executor = YsparrModelExecutor()
    task = AgentLoopTask(
        id="loop_1",
        owner_user_id=1,
        title="Check things",
        prompt="Do the thing.",
        contact_kind="agent",
        contact_id="1",
        agent_id=1,
    )
    request = ModelRequest(task_id="loop_1", task=task, turn_index=1)

    system_prompt = executor._build_system_prompt(request)

    assert "Keep each turn concise" in system_prompt
    assert "Prefer a short, actionable response" in system_prompt
