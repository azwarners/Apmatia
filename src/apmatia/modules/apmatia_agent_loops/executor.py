from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from apmatia.lib.apmatia_core.models import utc_now

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

    def execute(
        self,
        request: AgentLoopExecutionRequest,
        cancellation: CancellationToken,
    ) -> AgentLoopExecutionResult:
        task = self._load_task(request.task_id)
        task = self._mark_running(task)
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
                            result = ToolResult(
                                tool_name=tool_request.tool_name,
                                call_id=tool_request.call_id,
                                status="failed",
                                error=str(exc),
                        )
                        self._check_cancelled(task, cancellation)
                        tool_results.append(result)
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
