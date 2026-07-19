from __future__ import annotations

import json
import os
import re
import sys
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Callable

from apmatia.core.agent_management_runtime import get_agent_manager
from apmatia.core.model_management_runtime import get_llm_config_manager
from apmatia.lib.apmatia_core.models import utc_now
from apmatia.lib.agent_management.agent_prompt import default_agent_prompt
from apmatia.lib.persistence import logger as persistence_logger
from apmatia.lib.tool_management.models import ToolCall as RuntimeToolCall

from .executor import AgentLoopExecutor
from .models import (
    AgentLoopExecutionRequest,
    AgentLoopExecutionResult,
    AgentLoopTask,
    CancellationToken,
    ExecutionStatus,
    LoopEvent,
    LoopEventType,
    ToolDefinition,
    ToolResult,
    ToolRequest,
    TaskStatus,
    new_task_id,
)
from .ports import AgentLoopTaskRepository, ModelExecutor, ToolExecutor
from .repository import FileAgentLoopTaskRepository
from .state import resolve_agent_loop_workspace_root, resolve_contact_roots

try:
    from ysparr.core.types import PromptRequest
    from ysparr.modalities.text2text.backends.koboldcpp_backend import KoboldCppBackend
    from ysparr.modalities.text2text.backends.openai_compatible_backend import OpenAICompatibleBackend
    from ysparr.modalities.text2text.executor import execute
    from ysparr.modalities.text2text.storage import TextFileStorage
except ModuleNotFoundError:
    ysparr_src = Path(__file__).resolve().parents[4] / "src" / "apmatia" / "lib" / "ysparr"
    if str(ysparr_src) not in sys.path:
        sys.path.append(str(ysparr_src))

    from ysparr.core.types import PromptRequest
    from ysparr.modalities.text2text.backends.koboldcpp_backend import KoboldCppBackend
    from ysparr.modalities.text2text.backends.openai_compatible_backend import OpenAICompatibleBackend
    from ysparr.modalities.text2text.executor import execute
    from ysparr.modalities.text2text.storage import TextFileStorage


TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
_TOOL_CALL_START = "<tool_call>"
_TOOL_CALL_END = "</tool_call>"
_MAX_AGENT_LOOP_RESPONSE_SIZE = 1024


@dataclass(slots=True)
class LoopTaskRequest:
    owner_user_id: int
    contact_kind: str
    contact_id: int | str
    title: str
    prompt: str
    checklist: list[dict[str, Any]] | None = None
    participant_agent_ids: list[int] | None = None
    agent_id: int | None = None
    chat_mode: str = "single"
    allow_tools: bool = True
    max_iterations: int = 10
    member_group_ids: set[int] | None = None
    max_tool_calls: int = 10
    timeout_seconds: float | None = None
    selected_model_id: int | None = None
    workspace_root: str | None = None


class EventCancellationToken(CancellationToken):
    def __init__(self) -> None:
        self._event = Event()
        self._stop_hooks: list[Callable[[], None]] = []
        self._stop_hooks_lock = Lock()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def register_stop_hook(self, callback: Callable[[], None]) -> None:
        with self._stop_hooks_lock:
            self._stop_hooks.append(callback)
        if self._event.is_set():
            self._invoke_stop_hooks()

    def cancel(self) -> None:
        self._event.set()
        self._invoke_stop_hooks()

    def _invoke_stop_hooks(self) -> None:
        with self._stop_hooks_lock:
            hooks = list(self._stop_hooks)
        for hook in hooks:
            try:
                hook()
            except Exception:
                continue


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


class DefaultStaticModelExecutor:
    def generate(self, request, cancellation):  # type: ignore[no-untyped-def]
        from .models import ModelResponse, ModelUsage

        summary = f"{request.task.title or 'Task'} completed."
        if request.turn_index == 1 and request.task.prompt:
            summary = request.task.prompt.strip()
        if request.tool_results:
            summary = "\n".join(
                [
                    summary,
                    "Tool results:",
                    *[f"- {result.tool_name}: {result.status}" for result in request.tool_results],
                ]
            )
        return ModelResponse(
            final_text=summary,
            usage=ModelUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            raw_response={"mode": "static"},
        )


def prompt_llm(
    prompt: str = "Hello",
    output_dir: str | None = None,
    prompt_id: str | None = None,
    append_existing: bool = False,
    context: str | None = None,
    request_metadata: dict[str, Any] | None = None,
    llm_config=None,
    stop_event: Event | None = None,
    cancellation_token: EventCancellationToken | None = None,
    on_chunk: Callable[[str], None] | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    if context and context.strip():
        prompt_text = f"{context.rstrip()}\nUser: {prompt}\nAssistant:"
    else:
        prompt_text = f"User: {prompt}\nAssistant:"

    request = PromptRequest(
        prompt_id=prompt_id or str(uuid.uuid4()),
        prompt_text=prompt_text,
        model_name=_resolve_model_name(llm_config),
        parameters=_default_generation_parameters(llm_config),
        metadata={
            "append_existing": append_existing,
            **(request_metadata or {}),
            "on_event": on_event,
        },
        stop_event=stop_event,
    )

    backend = _build_backend(llm_config)
    if cancellation_token is not None and hasattr(cancellation_token, "register_stop_hook") and callable(getattr(cancellation_token, "register_stop_hook")):
        cancellation_token.register_stop_hook(lambda: _stop_backend_request(backend, request.prompt_id))
    apmatia_home = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
    resolved_output_dir = Path(output_dir).expanduser() if output_dir is not None else apmatia_home / "prompt_logs"
    storage = TextFileStorage(str(resolved_output_dir))
    if on_chunk is not None:
        storage = _ChunkCallbackStorage(str(resolved_output_dir), on_chunk=on_chunk)

    result = execute(request, backend, storage)
    raw_text = Path(result.output_path).read_text(encoding="utf-8").strip()

    if append_existing:
        return raw_text

    try:
        payload = json.loads(raw_text)
        return payload["results"][0]["text"].strip()
    except Exception:
        return raw_text


class YsparrModelExecutor:
    def __init__(self) -> None:
        self._fallback_executor = DefaultStaticModelExecutor()

    def generate(self, request, cancellation):  # type: ignore[no-untyped-def]
        llm_config = _limit_agent_loop_response_size(self._resolve_llm_config(request.task))
        if llm_config is None:
            return self._fallback_executor.generate(request, cancellation)

        system_prompt = self._build_system_prompt(request)
        user_prompt = self._build_user_prompt(request)
        stop_event = getattr(cancellation, "_event", None)
        stream_filter = ToolCallStreamFilter()
        live_activity: dict[str, Any] = {"text": "", "stats": {}}

        def _emit_live_activity() -> None:
            if not callable(getattr(request, "activity_sink", None)):
                return
            payload: dict[str, Any] = {
                "provider": live_activity.get("provider"),
                "endpoint": live_activity.get("endpoint"),
                "text": live_activity.get("text") or "",
                "stats": live_activity.get("stats") or {},
            }
            request.activity_sink(payload)

        def _record_chunk(chunk: str) -> None:
            visible_chunk = stream_filter.push(chunk)
            if not visible_chunk:
                return
            live_activity["text"] = f"{live_activity.get('text') or ''}{visible_chunk}"
            _emit_live_activity()

        def _record_event(event: dict[str, Any]) -> None:
            if not isinstance(event, dict):
                return
            provider = str(event.get("provider") or "").strip()
            endpoint = str(event.get("endpoint") or "").strip()
            if provider:
                live_activity["provider"] = provider
            if endpoint:
                live_activity["endpoint"] = endpoint
            stats = event.get("stats")
            if stats not in (None, {}, []):
                live_activity["stats"] = stats
            if event.get("text") and not live_activity.get("text"):
                live_activity["text"] = str(event.get("text") or "")
            _emit_live_activity()

        reply_text = prompt_llm(
            prompt=user_prompt,
            context=system_prompt,
            llm_config=llm_config,
            stop_event=stop_event if isinstance(stop_event, Event) else None,
            cancellation_token=cancellation if isinstance(cancellation, EventCancellationToken) else None,
            on_chunk=_record_chunk,
            on_event=_record_event,
            request_metadata={
                "agent_loop_task_id": request.task_id,
                "agent_loop_turn_index": request.turn_index,
                "agent_loop_task": request.task.to_dict(),
                "agent_loop_available_tools": [tool.to_dict() for tool in request.available_tools],
                "agent_loop_tool_results": [result.to_dict() for result in request.tool_results],
                "agent_loop_prior_events": [event.to_dict() for event in request.prior_events],
                "chat_messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        ).strip()
        tool_requests = tuple(parse_tool_calls(reply_text))
        final_text = strip_tool_calls(reply_text).strip() or None
        if not tool_requests and not final_text:
            return self._fallback_executor.generate(request, cancellation)
        return self._build_response(
            request=request,
            reply_text=reply_text,
            tool_requests=tool_requests,
            final_text=final_text,
            llm_config=llm_config,
        )

    def _resolve_llm_config(self, task: AgentLoopTask):
        agent_manager = get_agent_manager()
        llm_manager = get_llm_config_manager()

        if task.selected_model_id is not None:
            llm_config = llm_manager.get_config(int(task.selected_model_id))
            if llm_config is None:
                raise ValueError(f"Selected model not found: {task.selected_model_id}")
            return llm_config

        candidate_agent_ids: list[int] = []
        if task.agent_id is not None:
            candidate_agent_ids.append(int(task.agent_id))
        candidate_agent_ids.extend(int(agent_id) for agent_id in task.participant_agent_ids if agent_id is not None)

        for agent_id in candidate_agent_ids:
            agent = agent_manager.get_agent(agent_id)
            if agent is None:
                continue
            candidate_model_id = agent.active_model_id or agent.default_model_id
            if candidate_model_id is None:
                continue
            llm_config = llm_manager.get_config(int(candidate_model_id))
            if llm_config is not None:
                return llm_config

        configs = llm_manager.list_configs()
        return configs[0] if configs else None

    def _build_system_prompt(self, request) -> str:  # type: ignore[no-untyped-def]
        task = request.task
        identity_prompt = self._resolve_agent_identity_prompt(task)
        task_summary_lines = self._build_task_brief_lines(task)
        task_summary_lines.extend(
            [
                "Keep working across turns until the checklist is fully complete.",
                "Keep each turn concise and move to the next step quickly.",
                "Prefer a short, actionable response instead of a long explanation.",
                "If a workspace write fails because of permission or path errors, do not retry the same write unchanged; explain the blocker and choose a different approach or stop.",
                "At the end of every turn, include a <loop_status> JSON block with keys: "
                '"done", "summary", "completed_items", "remaining_items", "next_action", and "executive_analysis".',
                "Only set done to true when every checklist item is complete.",
                "When done is false, continue with the next step instead of concluding the task.",
            ]
        )
        base_prompt = "\n".join(task_summary_lines)
        if identity_prompt:
            base_prompt = f"{identity_prompt}\n\n{base_prompt}"
        return extend_system_prompt_with_tools(base_prompt, [tool for tool in request.available_tools])

    def _build_user_prompt(self, request) -> str:  # type: ignore[no-untyped-def]
        lines = [
            "Latest turn state:",
            f"- turn_index: {request.turn_index}",
            f"- max_model_turns: {int(request.task.max_model_turns or 1)}",
            f"- status: {request.task.status.value if hasattr(request.task.status, 'value') else request.task.status}",
            f"- execution_status: {request.task.execution_status.value if hasattr(request.task.execution_status, 'value') else request.task.execution_status}",
        ]
        if request.tool_results:
            lines.append("Tool results from the previous turn:")
            for result in request.tool_results:
                payload = result.output if result.output is not None else result.error
                lines.append(f"- {result.tool_name} [{result.status}]: {payload}")
        loop_status = request.task.metadata.get("loop_status") if isinstance(request.task.metadata, dict) else None
        if isinstance(loop_status, dict) and loop_status:
            lines.append("Current loop status JSON:")
            lines.append(json.dumps(loop_status, indent=2, ensure_ascii=False))
        if request.prior_events:
            lines.append("Recent execution events:")
            for event in request.prior_events[-8:]:
                lines.append(f"- {event.event_type.value}: {event.payload}")
        lines.append("Respond with the next step for the task and include the required <loop_status> block.")
        return "\n".join(lines)

    def _build_task_brief_lines(self, task: AgentLoopTask) -> list[str]:
        lines = [
            f"You are executing an autonomous agent loop task titled: {task.title or 'Untitled Task'}.",
            f"Task prompt: {task.prompt or '(no prompt provided)'}",
            f"Contact kind: {task.contact_kind or 'unknown'}",
            f"Contact ID: {task.contact_id if task.contact_id is not None else 'unknown'}",
        ]
        if task.checklist:
            lines.append("Checklist:")
            for index, item in enumerate(task.checklist, start=1):
                label = str(item.get("label") or item.get("title") or item.get("text") or f"Item {index}").strip()
                status = "done" if bool(item.get("done")) else "open"
                lines.append(f"- [{status}] {label}")
        else:
            lines.append("Checklist: none provided.")
        return lines

    def _build_response(self, *, request, reply_text: str, tool_requests: tuple, final_text: str | None, llm_config) -> "ModelResponse":  # type: ignore[no-untyped-def]
        from .models import ModelResponse

        return ModelResponse(
            final_text=final_text,
            tool_requests=tuple(
                ToolRequest(tool_name=tool_call.name, arguments=dict(tool_call.arguments))
                for tool_call in tool_requests
            ),
            raw_response={
                "mode": "ysparr",
                "reply_text": reply_text,
                "model_id": getattr(llm_config, "id", None),
                "provider_name": getattr(llm_config, "provider_name", ""),
                "backend": getattr(llm_config, "backend", ""),
                "selected_model_id": getattr(request.task, "selected_model_id", None),
            },
        )

    def _resolve_agent_identity_prompt(self, task: AgentLoopTask) -> str:
        agent_manager = get_agent_manager()
        candidate_agent_ids: list[int] = []
        if task.agent_id is not None:
            candidate_agent_ids.append(int(task.agent_id))
        candidate_agent_ids.extend(int(agent_id) for agent_id in task.participant_agent_ids if agent_id is not None)

        for agent_id in candidate_agent_ids:
            agent = agent_manager.get_agent(agent_id)
            if agent is None:
                continue
            if hasattr(agent_manager, "get_agent_system_prompt"):
                try:
                    prompt_text = str(agent_manager.get_agent_system_prompt(agent_id) or "").strip()
                    if prompt_text:
                        return prompt_text
                except Exception:
                    pass
            prompt_id = getattr(agent, "prompt_id", None)
            prompt = None
            if prompt_id is not None and hasattr(agent_manager, "get_prompt"):
                try:
                    prompt = agent_manager.get_prompt(int(prompt_id))
                except Exception:
                    prompt = None
            if prompt is None:
                prompt = default_agent_prompt()
            return agent_manager.compile_agent_system_prompt(getattr(agent, "name", "") or "an AI assistant", prompt)
        return ""


def _resolve_model_name(llm_config) -> str:
    if llm_config is not None:
        provider_name = str(getattr(llm_config, "provider_name", "") or "").strip()
        if not provider_name:
            provider_name = str(getattr(llm_config, "provider_model_name", "") or "").strip()
        if provider_name:
            return provider_name
        model_name = str(getattr(llm_config, "user_alias", "") or "").strip()
        if not model_name:
            model_name = str(getattr(llm_config, "model_name", "") or "").strip()
        if model_name:
            return model_name
    return "default"


def _build_backend(llm_config=None):
    backend_name = (
        (llm_config.backend if llm_config is not None else None)
        or "openai_compatible"
    ).strip().lower()

    if backend_name in {"openai", "openai_compatible", "openai-compatible"}:
        return OpenAICompatibleBackend(
            base_url=(llm_config.model_url if llm_config is not None else None),
            api_key=(llm_config.api_key if llm_config is not None else None),
            model_name=_resolve_model_name(llm_config),
            timeout_seconds=None,
        )

    return KoboldCppBackend(
        base_url=(llm_config.model_url if llm_config is not None else None) or "http://localhost:5001"
    )


def _default_generation_parameters(llm_config=None) -> dict[str, Any]:
    max_tokens_value = (llm_config.max_response_size if llm_config is not None else None) or 8192
    return {"max_tokens": int(max_tokens_value)}


def _limit_agent_loop_response_size(llm_config):
    if llm_config is None:
        return None
    max_response_size = int(getattr(llm_config, "max_response_size", 0) or _MAX_AGENT_LOOP_RESPONSE_SIZE)
    return replace(llm_config, max_response_size=min(max_response_size, _MAX_AGENT_LOOP_RESPONSE_SIZE))


def extend_system_prompt_with_tools(system_prompt: str, tools: list[Any]) -> str:
    tool_instructions = _build_tool_runtime_instructions(tools)
    if not tool_instructions:
        return system_prompt
    base = system_prompt.strip()
    if not base:
        return tool_instructions
    return f"{base}\n\n{tool_instructions}"


def _build_tool_runtime_instructions(tools: list[Any]) -> str:
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


def parse_tool_calls(text: str) -> list["ParsedToolCall"]:
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
    return TOOL_CALL_RE.sub("", text or "").strip()


@dataclass(slots=True)
class ParsedToolCall:
    name: str
    arguments: dict[str, Any]


class _ChunkCallbackStorage(TextFileStorage):
    def __init__(self, output_dir: str, *, on_chunk: Callable[[str], None] | None = None) -> None:
        super().__init__(output_dir)
        self._on_chunk = on_chunk

    def append(self, request: PromptRequest, text: str) -> None:
        super().append(request, text)
        if self._on_chunk is not None and text:
            self._on_chunk(text)


def _stop_backend_request(backend: Any, prompt_id: str) -> None:
    stop = getattr(backend, "stop", None)
    if not callable(stop):
        return
    try:
        stop(prompt_id)
    except Exception:
        return


class NullToolExecutor:
    def list_tools(self, context):  # type: ignore[no-untyped-def]
        return ()

    def execute(self, request, context, cancellation):  # type: ignore[no-untyped-def]
        from .models import ToolResult

        return ToolResult(
            tool_name=request.tool_name,
            call_id=request.call_id,
            status="failed",
            error="No tool executor is configured.",
        )


class ToolManagerToolExecutor:
    def list_tools(self, context):  # type: ignore[no-untyped-def]
        agent_id = _resolve_context_agent_id(getattr(context, "task", None))
        if agent_id is None:
            return ()
        from apmatia.core.tool_management_runtime import get_tool_manager

        tool_manager = get_tool_manager()
        tools = tool_manager.list_tools_available_to_agent(agent_id)
        return tuple(
            ToolDefinition(
                name=str(tool.name or "").strip(),
                description=str(tool.description or "").strip(),
                input_schema=dict(getattr(tool, "input_schema", {}) or {}),
                metadata={
                    **dict(getattr(tool, "metadata", {}) or {}),
                    "tool_id": tool.id,
                    "provider_id": tool.provider_id,
                    "confirmation_required": tool.confirmation_required,
                    "read_only": tool.read_only,
                },
            )
            for tool in tools
            if getattr(tool, "id", None) is not None and str(tool.name or "").strip()
        )

    def execute(self, request, context, cancellation):  # type: ignore[no-untyped-def]
        from apmatia.core.tool_management_runtime import get_tool_manager

        agent_id = _resolve_context_agent_id(getattr(context, "task", None))
        if agent_id is None:
            return self._missing_agent_result(request)

        tool_manager = get_tool_manager()
        tool = self._resolve_tool(tool_manager.list_tools_available_to_agent(agent_id), request.tool_name)
        if tool is None or getattr(tool, "id", None) is None:
            return self._missing_tool_result(request)

        runtime_call = RuntimeToolCall(
            tool_id=int(tool.id),
            arguments=dict(getattr(request, "arguments", {}) or {}),
            requester_agent_id=agent_id,
        )
        result = tool_manager.execute_tool_call(runtime_call)
        return ToolResult(
            tool_name=request.tool_name,
            call_id=runtime_call.call_id,
            status=str(getattr(result, "status", "failed")),
            output=getattr(result, "result", None),
            error=getattr(result, "error", None),
            metadata=dict(getattr(result, "metadata", {}) or {}),
        )

    @staticmethod
    def _resolve_tool(tools, tool_name: str):  # type: ignore[no-untyped-def]
        needle = str(tool_name or "").strip()
        for tool in tools:
            if str(getattr(tool, "name", "") or "").strip() == needle:
                return tool
        return None

    @staticmethod
    def _missing_agent_result(request):  # type: ignore[no-untyped-def]
        return ToolResult(
            tool_name=request.tool_name,
            call_id=getattr(request, "call_id", ""),
            status="failed",
            error="Unable to resolve the active agent for tool execution.",
        )

    @staticmethod
    def _missing_tool_result(request):  # type: ignore[no-untyped-def]
        return ToolResult(
            tool_name=request.tool_name,
            call_id=getattr(request, "call_id", ""),
            status="failed",
            error=f"Tool not available for this agent: {request.tool_name}",
        )


def _resolve_context_agent_id(task: AgentLoopTask | None) -> int | None:
    if task is None:
        return None
    if getattr(task, "agent_id", None) is not None:
        try:
            return int(task.agent_id)
        except Exception:
            return None
    participant_ids = getattr(task, "participant_agent_ids", ()) or ()
    for participant_id in participant_ids:
        try:
            return int(participant_id)
        except Exception:
            continue
    return None


class AgentLoopRuntime:
    def __init__(
        self,
        repository: AgentLoopTaskRepository | None = None,
        model_executor: ModelExecutor | None = None,
        tool_executor: ToolExecutor | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self._workspace_root = _ensure_agent_loop_workspace_root(workspace_root or resolve_agent_loop_workspace_root())
        persistence_logger.configure_agent_loop_logging()
        self._repository = repository or FileAgentLoopTaskRepository(self._workspace_root)
        self._model_executor = model_executor or YsparrModelExecutor()
        self._tool_executor = tool_executor or ToolManagerToolExecutor()
        self._executor = AgentLoopExecutor(self._repository, self._model_executor, self._tool_executor)
        self._lock = Lock()
        self._tokens: dict[str, EventCancellationToken] = {}
        self._threads: dict[str, Thread] = {}

    def start_task(self, request: LoopTaskRequest) -> dict[str, Any]:
        task = self._build_task(request)
        token = EventCancellationToken()
        self._repository.save(task)
        with self._lock:
            self._tokens[str(task.id or "")] = token
            thread = Thread(
                target=self._run_task,
                args=(str(task.id or ""), token),
                name=f"apmatia-agent-loop-{task.id}",
                daemon=True,
            )
            self._threads[str(task.id or "")] = thread
            thread.start()
        return self.get_task(str(task.id or "")) or task.to_dict()

    def start_loop(self, *, agent_id: int, prompt: str, model_id: int | None = None) -> dict[str, Any]:
        agent = get_agent_manager().get_agent(int(agent_id))
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")

        workspace_root = str(agent.workspace_root or "").strip()
        if not workspace_root:
            workspace_root = str(self._workspace_root / "agents" / f"agent-{int(agent.id or agent_id)}")

        task = AgentLoopTask(
            id=new_task_id(),
            owner_user_id=agent.owner_user_id,
            owner_group_id=agent.owner_group_id,
            mode=agent.mode,
            title=f"Alarm run for {agent.name or f'Agent {agent_id}'}",
            contact_kind="agent",
            contact_id=str(agent_id),
            prompt=str(prompt or "").strip(),
            checklist=(),
            participant_agent_ids=(),
            agent_id=int(agent_id),
            selected_model_id=None if model_id is None else int(model_id),
            chat_mode="single",
            allow_tools=True,
            max_model_turns=5,
            max_tool_calls=10,
            status=TaskStatus.QUEUED,
            execution_status=ExecutionStatus.PENDING,
            workspace_root=workspace_root,
            knowledge_root="",
            metadata={"source": "agent_alarms"},
        )
        token = EventCancellationToken()
        self._repository.save(task)
        with self._lock:
            self._tokens[str(task.id or "")] = token
            thread = Thread(
                target=self._run_task,
                args=(str(task.id or ""), token),
                name=f"apmatia-agent-loop-{task.id}",
                daemon=True,
            )
            self._threads[str(task.id or "")] = thread
            thread.start()
        return self.get_loop_run(str(task.id or "")) or task.to_dict()

    def list_tasks(self, *, contact_kind: str | None = None, contact_id: int | str | None = None) -> list[dict[str, Any]]:
        tasks = self._repository.list_all()
        if contact_kind is not None:
            tasks = [task for task in tasks if task.contact_kind == contact_kind]
        if contact_id is not None:
            tasks = [task for task in tasks if str(task.contact_id) == str(contact_id)]
        return [task.to_dict() for task in tasks]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        task = self._repository.get(task_id)
        return None if task is None else task.to_dict()

    def get_loop_run(self, run_id: str) -> dict[str, Any] | None:
        return self.get_task(run_id)

    def stop_task(self, task_id: str) -> dict[str, Any] | None:
        task = self._repository.get(task_id)
        if task is None:
            return None
        if task.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.LIMIT_REACHED,
        }:
            return task.to_dict()
        with self._lock:
            token = self._tokens.get(task_id)
            thread = self._threads.get(task_id)
            if token is not None:
                token.cancel()
        if thread is None or not thread.is_alive():
            task = replace(
                task,
                status=TaskStatus.CANCELLED,
                execution_status=ExecutionStatus.CANCELLED,
                stop_requested=True,
                last_error="Execution cancelled.",
                updated_at=utc_now(),
            )
            self._repository.save(task)
            self._repository.append_event(task_id, LoopEvent(LoopEventType.CANCELLATION_REQUESTED, task_id, {}))
            return task.to_dict()
        task = replace(task, status=TaskStatus.STOPPING, execution_status=ExecutionStatus.RUNNING, stop_requested=True, updated_at=utc_now())
        self._repository.save(task)
        self._repository.append_event(task_id, LoopEvent(LoopEventType.CANCELLATION_REQUESTED, task_id, {}))
        return task.to_dict()

    def wait_for_task(self, task_id: str, timeout: float | None = None) -> bool:
        with self._lock:
            thread = self._threads.get(task_id)
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def get_task_transcript(self, task_id: str) -> dict[str, Any] | None:
        task = self._repository.get(task_id)
        if task is None:
            return None
        messages: list[dict[str, Any]] = []
        for event in task.events:
            if event.event_type == LoopEventType.MODEL_TURN_COMPLETED:
                payload = event.payload
                text = str(payload.get("final_text") or "").strip()
                if text:
                    messages.append(
                        {
                            "role": "assistant",
                            "text": text,
                            "turn_index": payload.get("turn_index"),
                            "usage": payload.get("usage"),
                        }
                    )
            elif event.event_type in {LoopEventType.TOOL_COMPLETED, LoopEventType.TOOL_FAILED}:
                messages.append(
                    {
                        "role": "tool",
                        "text": str(event.payload.get("output") or event.payload.get("error") or ""),
                        "tool_name": event.payload.get("tool_name"),
                        "status": event.payload.get("status"),
                    }
                )
        content = "\n\n".join(message["text"] for message in messages if str(message.get("text") or "").strip())
        return {
            "task_id": task_id,
            "task": task.to_dict(),
            "messages": messages,
            "content": content,
        }

    def _run_task(self, task_id: str, cancellation: EventCancellationToken) -> None:
        try:
            self._executor.execute(AgentLoopExecutionRequest(task_id=task_id), cancellation)
        except Exception as exc:  # pragma: no cover - background execution safety net
            task = self._repository.get(task_id)
            if task is None:
                return
            task = replace(
                task,
                status=TaskStatus.FAILED,
                execution_status=ExecutionStatus.FAILED,
                last_error=str(exc),
                updated_at=utc_now(),
            )
            self._repository.save(task)
            self._repository.append_event(task_id, LoopEvent(LoopEventType.TASK_FAILED, task_id, {"error": str(exc)}))
        finally:
            with self._lock:
                self._tokens.pop(task_id, None)
                self._threads.pop(task_id, None)

    def _build_task(self, request: LoopTaskRequest) -> AgentLoopTask:
        roots = resolve_contact_roots(request.contact_kind, request.contact_id)
        checklist = tuple(dict(item) for item in (request.checklist or []) if isinstance(item, dict))
        participant_ids = tuple(int(item) for item in (request.participant_agent_ids or []) if str(item).strip())
        task = AgentLoopTask(
            id=new_task_id(),
            owner_user_id=request.owner_user_id,
            contact_kind=request.contact_kind,
            contact_id=request.contact_id,
            title=request.title,
            prompt=request.prompt,
            checklist=checklist,
            participant_agent_ids=participant_ids,
            agent_id=request.agent_id,
            chat_mode=request.chat_mode,
            allow_tools=bool(request.allow_tools),
            max_model_turns=max(1, int(request.max_iterations)),
            max_tool_calls=max(1, int(request.max_tool_calls)),
            timeout_seconds=request.timeout_seconds,
            selected_model_id=request.selected_model_id,
            status=TaskStatus.QUEUED,
            execution_status=ExecutionStatus.PENDING,
            workspace_root=str(request.workspace_root or roots.workspace_root),
            knowledge_root=str(roots.knowledge_root),
            metadata={
                "member_group_ids": sorted(int(item) for item in (request.member_group_ids or set()) if str(item).strip()),
            },
        )
        return task


_runtime: AgentLoopRuntime | None = None


def get_agent_loop_runner() -> AgentLoopRuntime:
    global _runtime
    if _runtime is None:
        _runtime = AgentLoopRuntime()
    return _runtime


def start_agent_loop(*, agent_id: int, prompt: str, model_id: int | None = None) -> dict[str, Any]:
    return get_agent_loop_runner().start_loop(agent_id=agent_id, prompt=prompt, model_id=model_id)


def get_agent_loop_run(run_id: str) -> dict[str, Any] | None:
    return get_agent_loop_runner().get_loop_run(run_id)


def _ensure_agent_loop_workspace_root(root: Path) -> Path:
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"Agent loop workspace root is not writable: {root}") from exc
    if not os.access(root, os.W_OK | os.X_OK):
        raise RuntimeError(f"Agent loop workspace root is not writable: {root}")
    return root
