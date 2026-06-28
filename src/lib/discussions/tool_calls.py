from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
_TOOL_CALL_START = "<tool_call>"
_TOOL_CALL_END = "</tool_call>"


@dataclass(slots=True)
class ParsedToolCall:
    name: str
    arguments: dict[str, Any]


def build_tool_runtime_instructions(tools: list[Any]) -> str:
    if not tools:
        return ""

    lines = [
        "Tool calling is available for this discussion.",
        "When a tool is needed, reply with one or more <tool_call>{...}</tool_call> blocks and no other text.",
        'Each tool call JSON object must use the shape {"name": "<tool_name>", "arguments": {...}}.',
        "After tool results are returned, continue with a normal assistant reply and do not emit tool-call blocks unless another tool is needed.",
        "Available tools:",
    ]
    for tool in tools:
        name = str(getattr(tool, "name", "")).strip()
        description = str(getattr(tool, "description", "")).strip()
        schema = getattr(tool, "input_schema", {}) or {}
        lines.append(
            f"- {name}: {description or 'No description provided.'} "
            f"Input schema: {json.dumps(schema, sort_keys=True)}"
        )
    return "\n".join(lines)


def extend_system_prompt_with_tools(system_prompt: str, tools: list[Any]) -> str:
    tool_instructions = build_tool_runtime_instructions(tools)
    if not tool_instructions:
        return system_prompt
    base = system_prompt.strip()
    if not base:
        return tool_instructions
    return f"{base}\n\n{tool_instructions}"


def parse_tool_calls(text: str) -> list[ParsedToolCall]:
    calls: list[ParsedToolCall] = []
    for match in TOOL_CALL_RE.finditer(text or ""):
        payload = match.group(1).strip()
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if not isinstance(decoded, dict):
            continue
        name = str(decoded.get("name", "")).strip()
        arguments = decoded.get("arguments", {})
        if not name or not isinstance(arguments, dict):
            continue
        calls.append(ParsedToolCall(name=name, arguments=arguments))
    return calls


def strip_tool_calls(text: str) -> str:
    cleaned = TOOL_CALL_RE.sub("", text or "")
    return cleaned.strip()


def format_tool_result_message(tool_name: str, status: str, result: Any = None, error: str | None = None) -> str:
    payload = {
        "tool": tool_name,
        "status": status,
        "result": result,
        "error": error,
    }
    return (
        "Tool result:\n"
        f"{json.dumps(payload, ensure_ascii=True, sort_keys=True)}\n"
        "Use this result to continue answering the user."
    )


class ToolCallStreamFilter:
    def __init__(self) -> None:
        self._inside_tool_call = False
        self._pending = ""

    def push(self, chunk: str) -> str:
        self._pending += str(chunk or "")
        visible_parts: list[str] = []

        while self._pending:
            if self._inside_tool_call:
                end_index = self._pending.find(_TOOL_CALL_END)
                if end_index >= 0:
                    self._pending = self._pending[end_index + len(_TOOL_CALL_END) :]
                    self._inside_tool_call = False
                    continue

                keep = _longest_suffix_prefix(self._pending, _TOOL_CALL_END)
                self._pending = self._pending[-keep:] if keep else ""
                break

            start_index = self._pending.find(_TOOL_CALL_START)
            if start_index >= 0:
                visible_parts.append(self._pending[:start_index])
                self._pending = self._pending[start_index + len(_TOOL_CALL_START) :]
                self._inside_tool_call = True
                continue

            keep = _longest_suffix_prefix(self._pending, _TOOL_CALL_START)
            if keep:
                visible_parts.append(self._pending[:-keep])
                self._pending = self._pending[-keep:]
            else:
                visible_parts.append(self._pending)
                self._pending = ""
            break

        return "".join(visible_parts)

    def finalize(self) -> str:
        if self._inside_tool_call:
            self._pending = ""
            return ""
        final_text = self._pending
        self._pending = ""
        return final_text


def _longest_suffix_prefix(value: str, marker: str) -> int:
    max_length = min(len(value), len(marker) - 1)
    for length in range(max_length, 0, -1):
        if value.endswith(marker[:length]):
            return length
    return 0
