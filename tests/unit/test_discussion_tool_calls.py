from types import SimpleNamespace

from src.lib.discussions.tool_calls import (
    build_tool_runtime_instructions,
    extend_system_prompt_with_tools,
    format_tool_result_message,
    parse_tool_calls,
    strip_tool_calls,
    ToolCallStreamFilter,
)


def test_parse_tool_calls_reads_tagged_json_blocks():
    text = """
Before
<tool_call>{"name":"echo","arguments":{"text":"hello"}}</tool_call>
<tool_call>{"name":"get_current_time","arguments":{}}</tool_call>
After
"""

    parsed = parse_tool_calls(text)

    assert len(parsed) == 2
    assert parsed[0].name == "echo"
    assert parsed[0].arguments == {"text": "hello"}
    assert parsed[1].name == "get_current_time"
    assert parsed[1].arguments == {}


def test_strip_tool_calls_removes_tagged_blocks():
    text = 'Thinking...\n<tool_call>{"name":"echo","arguments":{"text":"hello"}}</tool_call>\nDone.'

    assert strip_tool_calls(text) == "Thinking...\n\nDone."


def test_extend_system_prompt_with_tools_lists_available_tools():
    tools = [
        SimpleNamespace(
            name="echo",
            description="Return the provided text.",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
        )
    ]

    result = extend_system_prompt_with_tools("You are Helper.", tools)

    assert "You are Helper." in result
    assert "Tool calling is available for this discussion." in result
    assert "- echo: Return the provided text." in result


def test_build_tool_runtime_instructions_empty_when_no_tools():
    assert build_tool_runtime_instructions([]) == ""


def test_format_tool_result_message_is_json_backed():
    message = format_tool_result_message("echo", "success", result={"text": "hello"})

    assert '"tool": "echo"' in message
    assert '"status": "success"' in message
    assert '"text": "hello"' in message


def test_tool_call_stream_filter_hides_tool_markup_incrementally():
    stream_filter = ToolCallStreamFilter()

    visible_a = stream_filter.push("Hello ")
    visible_b = stream_filter.push("<tool")
    visible_c = stream_filter.push('_call>{"name":"echo","arguments":{"text":"hi"}}</tool_call> world')
    visible_d = stream_filter.finalize()

    assert visible_a == "Hello "
    assert visible_b == ""
    assert visible_c == " world"
    assert visible_d == ""
