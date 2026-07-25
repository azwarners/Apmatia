from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from time import perf_counter

from apmatia.lib.apmatia_core.models import utc_now
from apmatia.modules.persistence import logger as persistence_logger

from .models import (
    AgentLoopExecutionRequest,
    AgentLoopExecutionResult,
    AgentLoopTask,
    CancellationToken,
    ExecutionStatus,
    LoopEvent,
    LoopEventType,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    TaskStatus,
    ToolContext,
    ToolRequest,
    ToolResult,
)
from .ports import AgentLoopTaskRepository, ModelExecutor, ToolExecutor


_LOOP_STATUS_RE = re.compile(r"<loop_status>\s*(?P<payload>.+?)\s*</loop_status>", re.DOTALL)


class AgentLoopExecutor:
    def __init__(
        self,
        repository: AgentLoopTaskRepository,
        model_executor: ModelExecutor,
        tool_executor: ToolExecutor,
    ) -> None:
        self._repository = repository
        self._model_executor = model_executor
        self._tool_executor = tool_executor
        self._logger = persistence_logger.get_agent_loop_logger()

    def execute(
        self,
        request: AgentLoopExecutionRequest,
        cancellation: CancellationToken,
    ) -> AgentLoopExecutionResult:
        task = self._load_task(request.task_id)
        task = self._mark_running(task)
        task_started_at = perf_counter()
        self._log(
            "info",
            "task_started",
            task_id=str(task.id or ""),
            title=task.title,
            contact_kind=task.contact_kind,
            contact_id=task.contact_id,
            max_model_turns=int(task.max_model_turns or 0),
            max_tool_calls=int(task.max_tool_calls or 0),
        )
        task = self._persist_event(
            task,
            LoopEvent(
                LoopEventType.TASK_STARTED,
                str(task.id or ""),
                {
                    "title": task.title,
                    "contact_kind": task.contact_kind,
                    "contact_id": task.contact_id,
                },
            ),
        )

        start_time = utc_now()
        tool_results_for_next_turn: tuple[ToolResult, ...] = ()
        model_turn_count = 0
        tool_call_count = 0

        try:
            while model_turn_count < int(task.max_model_turns):
                self._check_cancelled(task, cancellation)
                self._check_timeout(task, start_time)
                model_turn_count += 1
                turn_started_at = perf_counter()
                self._log(
                    "info",
                    "model_turn_started",
                    task_id=str(task.id or ""),
                    turn_index=model_turn_count,
                    tool_call_count=tool_call_count,
                    checklist_items=len(task.checklist or ()),
                )
                task = self._persist_event(
                    task,
                    LoopEvent(
                        LoopEventType.MODEL_TURN_STARTED,
                        str(task.id or ""),
                        {"turn_index": model_turn_count},
                    ),
                )
                task = self._latest_task(task)
                task = replace(task, current_turn=model_turn_count, updated_at=utc_now())
                self._repository.save(task)

                tool_context = self._build_tool_context(task, model_turn_count, tool_call_count)
                try:
                    available_tools = tuple(self._tool_executor.list_tools(tool_context))
                except Exception as exc:
                    task = self._finish_task(
                        task,
                        final_text=task.final_text,
                        status=TaskStatus.FAILED,
                        execution_status=ExecutionStatus.FAILED,
                        last_error=str(exc),
                    )
                    task = self._persist_event(
                        task,
                        LoopEvent(
                            LoopEventType.TASK_FAILED,
                            str(task.id or ""),
                            {
                                "stage": "tool_list",
                                "turn_index": model_turn_count,
                                "error": str(exc),
                            },
                        ),
                    )
                    return AgentLoopExecutionResult(
                        task_id=str(task.id or ""),
                        status=ExecutionStatus.FAILED,
                        final_text=task.final_text,
                        task=task,
                        events=task.events,
                        model_turns=model_turn_count,
                        tool_calls=tool_call_count,
                        stop_reason="tool_list_error",
                        raw_response=None,
                    )

                def _record_model_activity(activity: dict[str, Any]) -> None:
                    nonlocal task

                    payload = {
                        "provider": activity.get("provider"),
                        "endpoint": activity.get("endpoint"),
                        "text": activity.get("text"),
                        "stats": activity.get("stats"),
                    }
                    task = self._latest_task(task)
                    metadata = dict(task.metadata)
                    metadata["live_activity"] = payload
                    task = replace(task, metadata=metadata, updated_at=utc_now())
                    self._repository.save(task)
                    task = self._persist_event(
                        task,
                        LoopEvent(
                            LoopEventType.MODEL_ACTIVITY,
                            str(task.id or ""),
                            payload,
                        ),
                    )

                model_request = ModelRequest(
                    task_id=str(task.id or ""),
                    task=task,
                    turn_index=model_turn_count,
                    available_tools=available_tools,
                    tool_results=tool_results_for_next_turn,
                    prior_events=task.events,
                    activity_sink=_record_model_activity,
                )
                try:
                    response = self._model_executor.generate(model_request, cancellation)
                except Exception as exc:
                    elapsed_seconds = perf_counter() - turn_started_at
                    self._log_exception(
                        "model_turn_failed",
                        exc,
                        task_id=str(task.id or ""),
                        turn_index=model_turn_count,
                        elapsed_seconds=round(elapsed_seconds, 6),
                    )
                    task = self._finish_task(
                        task,
                        final_text=task.final_text,
                        status=TaskStatus.FAILED,
                        execution_status=ExecutionStatus.FAILED,
                        last_error=str(exc),
                    )
                    task = self._persist_event(
                        task,
                        LoopEvent(
                            LoopEventType.TASK_FAILED,
                            str(task.id or ""),
                            {
                                "stage": "model_generate",
                                "turn_index": model_turn_count,
                                "error": str(exc),
                            },
                        ),
                    )
                    return AgentLoopExecutionResult(
                        task_id=str(task.id or ""),
                        status=ExecutionStatus.FAILED,
                        final_text=task.final_text,
                        task=task,
                        events=task.events,
                        model_turns=model_turn_count,
                        tool_calls=tool_call_count,
                        stop_reason="model_error",
                        raw_response=None,
                    )
                self._check_cancelled(task, cancellation)
                turn_elapsed = max(perf_counter() - turn_started_at, 0.0)
                completion_text = response.final_text or ""
                usage = response.usage
                prompt_tokens = None if usage is None else usage.prompt_tokens
                completion_tokens = None if usage is None else usage.completion_tokens
                total_tokens = None if usage is None else usage.total_tokens
                completion_chars = len(completion_text)
                self._log(
                    "info",
                    "model_turn_completed",
                    task_id=str(task.id or ""),
                    turn_index=model_turn_count,
                    elapsed_seconds=round(turn_elapsed, 6),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    completion_chars=completion_chars,
                    completion_chars_per_second=self._rate(completion_chars, turn_elapsed),
                    completion_tokens_per_second=self._rate(completion_tokens, turn_elapsed),
                    tool_request_count=len(response.tool_requests),
                    final_text_preview=self._preview_text(completion_text),
                    loop_status=_parse_loop_status(completion_text),
                )
                task = self._persist_event(
                    task,
                    LoopEvent(
                        LoopEventType.MODEL_TURN_COMPLETED,
                        str(task.id or ""),
                        {
                            "turn_index": model_turn_count,
                            "final_text": response.final_text,
                            "tool_requests": [request.to_dict() for request in response.tool_requests],
                            "usage": None if response.usage is None else response.usage.to_dict(),
                            "loop_status": _parse_loop_status(response.final_text or ""),
                        },
                    ),
                )

                if response.tool_requests:
                    tool_results: list[ToolResult] = []
                    for tool_request in response.tool_requests:
                        self._check_cancelled(task, cancellation)
                        if tool_call_count >= int(task.max_tool_calls):
                            return self._finish_limit_reached(
                                task,
                                stop_reason="max_tool_calls",
                                turn_index=model_turn_count,
                                tool_call_count=tool_call_count,
                            )
                        tool_call_count += 1
                        tool_started_at = perf_counter()
                        self._log(
                            "info",
                            "tool_requested",
                            task_id=str(task.id or ""),
                            turn_index=model_turn_count,
                            tool_call_index=tool_call_count,
                            tool_name=tool_request.tool_name,
                            call_id=tool_request.call_id,
                            arguments=tool_request.arguments,
                        )
                        task = self._persist_event(
                            task,
                            LoopEvent(
                                LoopEventType.TOOL_REQUESTED,
                                str(task.id or ""),
                                {
                                    "turn_index": model_turn_count,
                                    "tool_call_index": tool_call_count,
                                    "tool_name": tool_request.tool_name,
                                    "call_id": tool_request.call_id,
                                    "arguments": tool_request.arguments,
                                },
                            ),
                        )
                        tool_context = self._build_tool_context(task, model_turn_count, tool_call_count)
                        try:
                            result = self._tool_executor.execute(tool_request, tool_context, cancellation)
                        except Exception as exc:  # pragma: no cover - defensive guard
                            tool_elapsed = perf_counter() - tool_started_at
                            self._log_exception(
                                "tool_failed",
                                exc,
                                task_id=str(task.id or ""),
                                turn_index=model_turn_count,
                                tool_call_index=tool_call_count,
                                tool_name=tool_request.tool_name,
                                call_id=tool_request.call_id,
                                elapsed_seconds=round(tool_elapsed, 6),
                            )
                            result = ToolResult(
                                tool_name=tool_request.tool_name,
                                call_id=tool_request.call_id,
                                status="failed",
                                error=str(exc),
                            )
                        self._check_cancelled(task, cancellation)
                        tool_results.append(result)
                        tool_elapsed = max(perf_counter() - tool_started_at, 0.0)
                        output_text = result.output if result.output is not None else result.error
                        output_preview = self._preview_text(output_text)
                        output_chars = len(str(output_text or ""))
                        self._log(
                            "info" if result.status == "success" else "warning",
                            "tool_completed" if result.status == "success" else "tool_failed",
                            task_id=str(task.id or ""),
                            turn_index=model_turn_count,
                            tool_call_index=tool_call_count,
                            tool_name=result.tool_name,
                            call_id=result.call_id,
                            status=result.status,
                            elapsed_seconds=round(tool_elapsed, 6),
                            output_chars=output_chars,
                            output_chars_per_second=self._rate(output_chars, tool_elapsed),
                            output_preview=output_preview,
                            error=result.error,
                            metadata=result.metadata,
                        )
                        task = self._latest_task(task)
                        task = replace(task, tool_call_count=tool_call_count, updated_at=utc_now())
                        self._repository.save(task)
                        event_type = LoopEventType.TOOL_COMPLETED if result.status == "success" else LoopEventType.TOOL_FAILED
                        task = self._persist_event(
                            task,
                            LoopEvent(
                                event_type,
                                str(task.id or ""),
                                {
                                    "tool_call_index": tool_call_count,
                                    "tool_name": result.tool_name,
                                    "call_id": result.call_id,
                                    "status": result.status,
                                    "output": result.output,
                                    "error": result.error,
                                    "metadata": result.metadata,
                                },
                            ),
                        )
                        if self._is_fatal_workspace_tool_failure(tool_request, result):
                            return self._finish_tool_failure(
                                task,
                                turn_index=model_turn_count,
                                tool_call_count=tool_call_count,
                                result=result,
                            )
                    tool_results_for_next_turn = tuple(tool_results)
                    continue

                self._check_cancelled(task, cancellation)
                final_text = response.final_text or ""
                loop_status = _parse_loop_status(final_text)
                visible_final_text = _strip_loop_status(final_text)
                should_continue = bool(task.checklist) and (not loop_status or not bool(loop_status.get("done")))
                metadata_updates: dict[str, Any] = {}
                if loop_status is not None:
                    metadata_updates["loop_status"] = loop_status
                    summary_value = str(loop_status.get("summary") or "").strip()
                    if summary_value:
                        metadata_updates["summary"] = summary_value
                    executive_analysis_value = str(loop_status.get("executive_analysis") or "").strip()
                    if executive_analysis_value:
                        metadata_updates["executive_analysis"] = executive_analysis_value
                if metadata_updates:
                    task = self._latest_task(task)
                    metadata = dict(task.metadata)
                    metadata.update(metadata_updates)
                    task = replace(task, metadata=metadata, updated_at=utc_now())
                    self._repository.save(task)
                if should_continue:
                    self._log(
                        "info",
                        "turn_continues",
                        task_id=str(task.id or ""),
                        turn_index=model_turn_count,
                        remaining_checklist_items=len(task.checklist or ()),
                        loop_status=loop_status,
                    )
                    tool_results_for_next_turn = ()
                    continue
                task = self._finish_task(
                    task,
                    final_text=visible_final_text,
                    status=TaskStatus.COMPLETED,
                    execution_status=ExecutionStatus.COMPLETED,
                    summary=metadata_updates.get("summary", visible_final_text),
                )
                task = self._persist_event(
                    task,
                    LoopEvent(
                        LoopEventType.TASK_COMPLETED,
                        str(task.id or ""),
                        {
                            "final_text": visible_final_text,
                            "turn_index": model_turn_count,
                            "tool_call_count": tool_call_count,
                            "loop_status": loop_status,
                        },
                    ),
                )
                self._log(
                    "info",
                    "task_completed",
                    task_id=str(task.id or ""),
                    turn_index=model_turn_count,
                    tool_call_count=tool_call_count,
                    elapsed_seconds=round(max(perf_counter() - task_started_at, 0.0), 6),
                    final_text_preview=self._preview_text(visible_final_text),
                    loop_status=loop_status,
                )
                return AgentLoopExecutionResult(
                    task_id=str(task.id or ""),
                    status=ExecutionStatus.COMPLETED,
                    final_text=visible_final_text,
                    task=task,
                    events=task.events,
                    model_turns=model_turn_count,
                    tool_calls=tool_call_count,
                    raw_response=response.raw_response,
                )

            return self._finish_limit_reached(
                task,
                stop_reason="max_model_turns",
                turn_index=model_turn_count,
                tool_call_count=tool_call_count,
            )
        except _CancelledExecution as exc:
            self._log(
                "warning",
                "task_cancelled",
                task_id=str(exc.task.id or ""),
                turn_index=model_turn_count,
                tool_call_count=tool_call_count,
                elapsed_seconds=round(max(perf_counter() - task_started_at, 0.0), 6),
            )
            return AgentLoopExecutionResult(
                task_id=str(exc.task.id or ""),
                status=ExecutionStatus.CANCELLED,
                final_text=exc.task.final_text,
                task=exc.task,
                events=exc.task.events,
                model_turns=model_turn_count,
                tool_calls=tool_call_count,
                stop_reason="cancelled",
            )
        except _LimitReachedExecution as exc:
            self._log(
                "warning",
                "execution_limit_reached",
                task_id=str(exc.task.id or ""),
                turn_index=model_turn_count,
                tool_call_count=tool_call_count,
                stop_reason=exc.stop_reason,
                elapsed_seconds=round(max(perf_counter() - task_started_at, 0.0), 6),
            )
            return self._finish_limit_reached(
                exc.task,
                stop_reason=exc.stop_reason,
                turn_index=model_turn_count,
                tool_call_count=tool_call_count,
            )

    def _load_task(self, task_id: str) -> AgentLoopTask:
        task = self._repository.get(task_id)
        if task is None:
            raise KeyError(f"Task not found: {task_id}")
        return task

    def _mark_running(self, task: AgentLoopTask) -> AgentLoopTask:
        task = replace(
            task,
            status=TaskStatus.RUNNING,
            execution_status=ExecutionStatus.RUNNING,
            updated_at=utc_now(),
        )
        self._repository.save(task)
        return task

    def _log(self, level: str, message: str, **extra: Any) -> None:
        payload = {key: value for key, value in extra.items() if value is not None}
        log_method = getattr(self._logger, level, self._logger.info)
        log_method(message, extra=payload)

    def _log_exception(self, message: str, exc: Exception, **extra: Any) -> None:
        payload = {key: value for key, value in extra.items() if value is not None}
        self._logger.exception(message, extra=payload)

    def _rate(self, amount: int | float | None, elapsed_seconds: float) -> float | None:
        if amount in (None, 0) or elapsed_seconds <= 0:
            return None
        return round(float(amount) / elapsed_seconds, 3)

    def _preview_text(self, value: Any, *, limit: int = 256) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        return f"{text[: limit - 1].rstrip()}…"

    def _finish_task(
        self,
        task: AgentLoopTask,
        *,
        final_text: str | None,
        status: TaskStatus,
        execution_status: ExecutionStatus,
        last_error: str | None = None,
        **updates: Any,
    ) -> AgentLoopTask:
        task = self._latest_task(task)
        if status != TaskStatus.CANCELLED and (task.stop_requested or task.status == TaskStatus.STOPPING):
            status = TaskStatus.CANCELLED
            execution_status = ExecutionStatus.CANCELLED
            last_error = last_error or "Execution cancelled."
        summary = updates.pop("summary", final_text if final_text is not None else task.summary)
        task = replace(
            task,
            status=status,
            execution_status=execution_status,
            final_text=final_text,
            summary=summary,
            last_error=last_error,
            updated_at=utc_now(),
            **updates,
        )
        self._repository.save(task)
        return task

    def _finish_limit_reached(
        self,
        task: AgentLoopTask,
        *,
        stop_reason: str,
        turn_index: int,
        tool_call_count: int,
    ) -> AgentLoopExecutionResult:
        task = self._finish_task(
            task,
            final_text=task.final_text,
            status=TaskStatus.LIMIT_REACHED,
            execution_status=ExecutionStatus.LIMIT_REACHED,
            last_error=f"Execution limit reached: {stop_reason}",
        )
        task = self._persist_event(
            task,
            LoopEvent(
                LoopEventType.EXECUTION_LIMIT_REACHED,
                str(task.id or ""),
                {
                    "stop_reason": stop_reason,
                    "turn_index": turn_index,
                    "tool_call_count": tool_call_count,
                },
            ),
        )
        return AgentLoopExecutionResult(
            task_id=str(task.id or ""),
            status=ExecutionStatus.LIMIT_REACHED,
            final_text=task.final_text,
            task=task,
            events=task.events,
            model_turns=turn_index,
            tool_calls=tool_call_count,
            stop_reason=stop_reason,
        )

    def _finish_tool_failure(
        self,
        task: AgentLoopTask,
        *,
        turn_index: int,
        tool_call_count: int,
        result: ToolResult,
    ) -> AgentLoopExecutionResult:
        stop_reason = self._tool_failure_stop_reason(result)
        last_error = self._tool_failure_message(result)
        task = self._finish_task(
            task,
            final_text=task.final_text,
            status=TaskStatus.FAILED,
            execution_status=ExecutionStatus.FAILED,
            last_error=last_error,
        )
        task = self._persist_event(
            task,
            LoopEvent(
                LoopEventType.TASK_FAILED,
                str(task.id or ""),
                {
                    "stage": "tool_execute",
                    "turn_index": turn_index,
                    "tool_call_index": tool_call_count,
                    "tool_name": result.tool_name,
                    "status": result.status,
                    "error": result.error,
                    "stop_reason": stop_reason,
                    "fatal": True,
                },
            ),
        )
        self._log(
            "warning",
            "task_failed",
            task_id=str(task.id or ""),
            turn_index=turn_index,
            tool_call_count=tool_call_count,
            stop_reason=stop_reason,
            last_error=last_error,
        )
        return AgentLoopExecutionResult(
            task_id=str(task.id or ""),
            status=ExecutionStatus.FAILED,
            final_text=task.final_text,
            task=task,
            events=task.events,
            model_turns=turn_index,
            tool_calls=tool_call_count,
            stop_reason=stop_reason,
            raw_response=None,
        )

    def _persist_event(self, task: AgentLoopTask, event: LoopEvent) -> AgentLoopTask:
        self._repository.append_event(str(task.id or ""), event)
        latest_task = self._repository.get(str(task.id or ""))
        if latest_task is not None:
            return latest_task
        return replace(task, events=(*task.events, event), updated_at=event.created_at)

    def _latest_task(self, task: AgentLoopTask) -> AgentLoopTask:
        return self._repository.get(str(task.id or "")) or task

    def _build_tool_context(self, task: AgentLoopTask, turn_index: int, tool_call_index: int) -> ToolContext:
        return ToolContext(
            task_id=str(task.id or ""),
            task=task,
            turn_index=turn_index,
            tool_call_index=tool_call_index,
            available_tools=tuple(
                self._tool_executor.list_tools(
                    ToolContext(task_id=str(task.id or ""), task=task, turn_index=turn_index, tool_call_index=tool_call_index)
                )
            ),
        )

    def _check_cancelled(self, task: AgentLoopTask, cancellation: CancellationToken) -> None:
        latest_task = self._repository.get(str(task.id or "")) or task
        if not cancellation.is_cancelled() and not bool(latest_task.stop_requested) and latest_task.status != TaskStatus.STOPPING:
            return
        task = self._finish_task(
            latest_task,
            final_text=task.final_text,
            status=TaskStatus.CANCELLED,
            execution_status=ExecutionStatus.CANCELLED,
            last_error="Execution cancelled.",
        )
        task = self._persist_event(
            task,
            LoopEvent(
                LoopEventType.CANCELLATION_REQUESTED,
                str(task.id or ""),
                {},
            ),
        )
        raise _CancelledExecution(task)

    def _check_timeout(self, task: AgentLoopTask, start_time: datetime) -> None:
        if task.timeout_seconds in (None, "", 0):
            return
        deadline = start_time.timestamp() + float(task.timeout_seconds)
        if datetime.now(timezone.utc).timestamp() <= deadline:
            return
        raise _LimitReachedExecution(task, "timeout")

    def _is_fatal_workspace_tool_failure(self, tool_request: ToolRequest, result: ToolResult) -> bool:
        if result.status == "success":
            return False
        if not str(tool_request.tool_name or "").startswith("workspace_"):
            return False
        error_code = self._tool_error_code(result.error)
        return error_code in {
            "PERMISSION_DENIED",
            "MISSING_WORKSPACE_DIRECTORY",
            "WORKSPACE_ROOT_ERROR",
            "WORKSPACE_PATH_ERROR",
        }

    def _tool_failure_stop_reason(self, result: ToolResult) -> str:
        error_code = self._tool_error_code(result.error)
        if error_code:
            return f"tool_error:{result.tool_name}:{error_code}"
        return f"tool_error:{result.tool_name}"

    def _tool_failure_message(self, result: ToolResult) -> str:
        error_code = self._tool_error_code(result.error)
        details = str(result.error or "").strip()
        if error_code:
            return f"{result.tool_name} failed with {error_code}: {details}"
        return f"{result.tool_name} failed: {details or 'unknown error'}"

    def _tool_error_code(self, error: Any) -> str | None:
        if isinstance(error, dict):
            code = str(error.get("code") or "").strip()
            return code or None
        if isinstance(error, str):
            upper_error = error.upper()
            for candidate in (
                "PERMISSION_DENIED",
                "MISSING_WORKSPACE_DIRECTORY",
                "WORKSPACE_ROOT_ERROR",
                "WORKSPACE_PATH_ERROR",
            ):
                if candidate in upper_error:
                    return candidate
        return None


def _parse_loop_status(text: str) -> dict[str, Any] | None:
    match = _LOOP_STATUS_RE.search(text or "")
    if match is None:
        return None
    payload = match.group("payload").strip()
    if not payload:
        return None
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _strip_loop_status(text: str) -> str:
    return _LOOP_STATUS_RE.sub("", text or "").strip()


class _CancelledExecution(RuntimeError):
    def __init__(self, task: AgentLoopTask) -> None:
        super().__init__("Execution cancelled.")
        self.task = task


class _LimitReachedExecution(RuntimeError):
    def __init__(self, task: AgentLoopTask, stop_reason: str) -> None:
        super().__init__(stop_reason)
        self.task = task
        self.stop_reason = stop_reason
