from __future__ import annotations

from apmatia.modules.ai_model_manager.models import LLMConfig as LLM
from apmatia.modules.agent_loops.models import AgentLoopTask, LoopEvent, LoopEventType, ModelRequest, ToolResult, ToolRequest
from apmatia.modules.agent_loops.service import YsparrModelExecutor, _limit_agent_loop_response_size


def test_agent_loop_response_size_preserves_configured_model_limit():
    config = LLM(id=1, user_alias="Test", backend="openai_compatible", max_response_size=8192)

    limited = _limit_agent_loop_response_size(config)

    assert limited is not None
    assert limited.max_response_size == 8192


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


def test_agent_loop_user_prompt_formats_roles_and_tool_calls():
    executor = YsparrModelExecutor()
    task = AgentLoopTask(id="loop_prompt", title="Prompt test", prompt="Original prompt")
    request = ModelRequest(
        task_id="loop_prompt",
        task=task,
        turn_index=2,
        tool_results=(
            ToolResult(
                tool_name="lookup",
                call_id="call_current",
                status="success",
                output={"value": "current result"},
            ),
        ),
        prior_events=(
            LoopEvent(LoopEventType.USER_MESSAGE, "loop_prompt", {"text": "Current user message"}),
            LoopEvent(
                LoopEventType.TOOL_REQUESTED,
                "loop_prompt",
                {"tool_name": "lookup", "arguments": {"query": "today"}},
            ),
            LoopEvent(
                LoopEventType.TOOL_RESULT,
                "loop_prompt",
                {
                    "tool_name": "lookup",
                    "call_id": "call_current",
                    "status": "success",
                    "output": {"value": "current result"},
                },
            ),
        ),
    )

    prompt = executor._build_user_prompt(request)

    assert "User: Current user message" in prompt
    assert 'Tool request (lookup): {"query": "today"}' in prompt
    assert 'Tool result (lookup, success): {"value": "current result"}' in prompt


def test_agent_loop_user_prompt_truncates_old_context_but_keeps_active_context():
    executor = YsparrModelExecutor()
    old_events = tuple(
        LoopEvent(
            LoopEventType.TOOL_RESULT,
            "loop_prompt",
            {
                "tool_name": "old_lookup",
                "call_id": f"old_{index}",
                "status": "success",
                "output": f"old context {index} " + ("x" * 1800),
            },
        )
        for index in range(12)
    )
    task = AgentLoopTask(id="loop_prompt", title="Prompt test")
    request = ModelRequest(
        task_id="loop_prompt",
        task=task,
        turn_index=3,
        tool_results=(
            ToolResult(
                tool_name="current_lookup",
                call_id="current_call",
                status="success",
                output="CURRENT TOOL OUTPUT " + ("y" * 5000),
            ),
        ),
        prior_events=(*old_events, LoopEvent(LoopEventType.USER_MESSAGE, "loop_prompt", {"text": "ACTIVE USER MESSAGE"})),
    )

    prompt = executor._build_user_prompt(request)

    assert "[Earlier conversation context truncated to fit the prompt budget.]" in prompt
    assert "ACTIVE USER MESSAGE" in prompt
    assert "CURRENT TOOL OUTPUT" in prompt
    assert "old context 0 " + ("x" * 1800) not in prompt
