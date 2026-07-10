from __future__ import annotations

import json
import re
import threading
import ctypes
from dataclasses import dataclass, field
from typing import Any

from apmatia.lib.discussions import discussion_state
from apmatia.core.tool_management_runtime import get_tool_manager
from apmatia.lib.tool_management.models import ToolCall

from .prompt_helpers import (
    build_loop_followup_prompt,
    build_loop_task_prompt,
    get_discussion_transcript,
    start_prompt_for_discussion,
    stop_prompt_for_discussion,
    wait_for_prompt_completion,
)
from .records import (
    LoopTaskRecord,
    list_task_records,
    new_task_id,
    save_task_record,
    task_directory,
    update_task_record,
)
from .state import resolve_contact_roots


_LOOP_STATUS_RE = re.compile(r"<loop_status>\s*(?P<payload>.+?)\s*</loop_status>", re.DOTALL)


@dataclass(slots=True)
class LoopTaskRequest:
    owner_user_id: int
    contact_kind: str
    contact_id: int | str
    title: str
    prompt: str
    checklist: list[dict[str, Any]] = field(default_factory=list)
    participant_agent_ids: list[int] = field(default_factory=list)
    agent_id: int | None = None
    chat_mode: str = "single"
    allow_tools: bool = True
    max_iterations: int = 5
    member_group_ids: set[int] = field(default_factory=set)


class ApmatiaAgentLoopRunner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}
        self._stop_requests: set[str] = set()

    def start_task(self, request: LoopTaskRequest) -> dict[str, Any]:
        record = self._create_record(request)
        save_task_record(record)
        thread = threading.Thread(target=self._run_task, args=(record.task_id,), daemon=True)
        with self._lock:
            self._threads[record.task_id] = thread
        thread.start()
        return record.to_dict()

    def list_tasks(
        self,
        *,
        contact_kind: str | None = None,
        contact_id: int | str | None = None,
    ) -> list[dict[str, Any]]:
        records = [record.to_dict() for record in list_task_records(contact_kind=contact_kind, contact_id=contact_id)]
        return [self._apply_runtime_overrides(record) for record in records]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        for record in list_task_records():
            if record.task_id == task_id:
                return self._apply_runtime_overrides(record.to_dict())
        return None

    def stop_task(self, task_id: str) -> dict[str, Any] | None:
        record = self._load_task(task_id)
        if record is None:
            return None

        with self._lock:
            thread = self._threads.get(task_id)
            self._stop_requests.add(task_id)

        if record.discussion_id:
            stop_prompt_for_discussion(record.discussion_id)

        returned_record = record.to_dict()
        if record.status not in {"completed", "failed", "stopped"}:
            try:
                persisted_record = update_task_record(
                    record,
                    stop_requested=True,
                    status="stopped",
                    completed_at=record.completed_at or record.updated_at,
                )
                returned_record = self._record_event(persisted_record, {"type": "stop_requested"}).to_dict()
            except OSError:
                returned_record = {
                    **returned_record,
                    "stop_requested": True,
                    "status": "stopped",
                    "completed_at": record.completed_at or record.updated_at,
                }

        if thread is not None and thread.is_alive():
            self._raise_system_exit_in_thread(thread)
        return self._apply_runtime_overrides(returned_record)

    def wait_for_task(self, task_id: str, timeout: float | None = None) -> bool:
        with self._lock:
            thread = self._threads.get(task_id)
        if thread is None:
            return True
        thread.join(timeout=timeout)
        return not thread.is_alive()

    def _create_record(self, request: LoopTaskRequest) -> LoopTaskRecord:
        contact_kind = str(request.contact_kind).strip().lower()
        if contact_kind not in {"agent", "group"}:
            raise ValueError("contact_kind must be either 'agent' or 'group'.")

        contact_roots = resolve_contact_roots(contact_kind, request.contact_id)
        if contact_kind == "group" and not request.participant_agent_ids:
            raise ValueError("Group loop tasks require participant_agent_ids.")

        task_id = new_task_id()
        checklist = _augment_checklist_for_verification(request.prompt, [dict(item) for item in request.checklist])
        task_root = task_directory(contact_kind, request.contact_id)
        task_root.mkdir(parents=True, exist_ok=True)
        record = LoopTaskRecord(
            task_id=task_id,
            owner_user_id=int(request.owner_user_id),
            contact_kind=contact_kind,
            contact_id=request.contact_id,
            title=request.title.strip() or "Untitled Loop Task",
            prompt=request.prompt.strip(),
            checklist=checklist,
            status="running",
            discussion_id=None,
            agent_id=request.agent_id,
            participant_agent_ids=[int(candidate) for candidate in request.participant_agent_ids],
            chat_mode=str(request.chat_mode or "single").strip() or "single",
            allow_tools=bool(request.allow_tools),
            max_iterations=max(1, int(request.max_iterations or 1)),
            workspace_root=str(contact_roots.workspace_root),
            knowledge_root=str(contact_roots.knowledge_root),
        )
        save_task_record(record)
        return record

    def _run_task(self, task_id: str) -> None:
        try:
            record = self._load_task(task_id)
            if record is None:
                return
            record = self._record_event(
                record,
                {
                    "type": "task_started",
                    "title": record.title,
                    "contact_kind": record.contact_kind,
                    "contact_id": record.contact_id,
                    "checklist": [dict(item) for item in record.checklist],
                },
            )
            if self._should_stop(record):
                record = update_task_record(record, status="stopped", completed_at=record.completed_at or record.updated_at)
                return
            discussion_id = self._ensure_discussion(record)
            record = update_task_record(
                record,
                discussion_id=discussion_id,
                last_error=None,
            )
            if self._should_stop(record):
                record = update_task_record(record, status="stopped", completed_at=record.completed_at or record.updated_at)
                return
            record = update_task_record(record, status="running")

            current_prompt = self._initial_prompt(record)
            for iteration in range(record.max_iterations):
                if self._should_stop(record):
                    record = update_task_record(
                        record,
                        status="stopped",
                        completed_at=record.completed_at or record.updated_at,
                    )
                    return
                record = update_task_record(record, current_iteration=iteration + 1)
                record = self._record_event(
                    record,
                    {
                        "type": "iteration_started",
                        "iteration": iteration + 1,
                        "max_iterations": record.max_iterations,
                    },
                )
                if self._should_stop(record):
                    record = update_task_record(
                        record,
                        status="stopped",
                        completed_at=record.completed_at or record.updated_at,
                    )
                    return
                start_prompt_for_discussion(
                    discussion_id=discussion_id,
                    prompt=current_prompt,
                    agent_id=record.agent_id,
                    allow_tools=record.allow_tools,
                )
                if not self._wait_for_prompt_completion_or_stop(task_id, discussion_id):
                    record = self._load_task(task_id) or record
                    record = update_task_record(
                        record,
                        status="stopped",
                        completed_at=record.completed_at or record.updated_at,
                    )
                    return
                record = self._load_task(task_id) or record
                if self._should_stop(record):
                    record = update_task_record(
                        record,
                        status="stopped",
                        completed_at=record.completed_at or record.updated_at,
                    )
                    return
                transcript = get_discussion_transcript(discussion_id)
                latest_status = self._latest_loop_status(transcript.get("messages", []))
                record = self._update_record_from_status(record, latest_status, transcript)
                if latest_status is not None:
                    record = self._record_event(
                        record,
                        {
                            "type": "loop_status",
                            "iteration": iteration + 1,
                            "status": dict(latest_status),
                        },
                    )
                if latest_status and bool(latest_status.get("done")):
                    record = update_task_record(
                        record,
                        status="completed",
                        completed_at=record.completed_at or record.updated_at,
                    )
                    return
                current_prompt = self._followup_prompt(record, latest_status)

            update_task_record(record, status="needs_review")
        except Exception as error:
            existing = self._load_task(task_id)
            if existing is not None:
                update_task_record(existing, status="failed", last_error=str(error))

        finally:
            with self._lock:
                self._threads.pop(task_id, None)

    def _ensure_discussion(self, record: LoopTaskRecord) -> str:
        discussion_title = record.title or "Loop Task"
        if record.contact_kind == "group":
            created = discussion_state.create_discussion(
                owner_user_id=record.owner_user_id,
                title=discussion_title,
                group_id=int(record.contact_id),
                participant_agent_ids=list(record.participant_agent_ids),
                chat_mode=record.chat_mode,
            )
            return str(created["discussion_id"])

        created = discussion_state.create_discussion(
            owner_user_id=record.owner_user_id,
            title=discussion_title,
            agent_id=record.agent_id,
            chat_mode="single",
        )
        return str(created["discussion_id"])

    def _initial_prompt(self, record: LoopTaskRecord) -> str:
        checklist_text = _format_checklist(record.checklist)
        return build_loop_task_prompt(
            title=record.title,
            contact_kind=record.contact_kind,
            contact_id=record.contact_id,
            workspace_root=str(record.workspace_root),
            knowledge_root=str(record.knowledge_root),
            prompt=record.prompt,
            checklist_text=checklist_text,
            allow_tools=record.allow_tools,
        )

    def _followup_prompt(self, record: LoopTaskRecord, loop_status: dict[str, Any] | None) -> str:
        remaining_items = []
        if isinstance(loop_status, dict):
            remaining_items = [str(item) for item in loop_status.get("remaining_items") or [] if str(item).strip()]
        remaining_text = "\n".join(f"- {item}" for item in remaining_items) or "- Continue from the current state."
        return build_loop_followup_prompt(title=record.title, remaining_items_text=remaining_text)

    def _update_record_from_status(
        self,
        record: LoopTaskRecord,
        loop_status: dict[str, Any] | None,
        transcript: dict[str, Any],
    ) -> LoopTaskRecord:
        latest_assistant_text = _latest_assistant_text(transcript.get("messages", []))
        summary = None
        executive_analysis = None
        if isinstance(loop_status, dict):
            summary = _optional_str(loop_status.get("summary"))
            executive_analysis = _optional_str(loop_status.get("executive_analysis"))
        if summary is None and latest_assistant_text:
            summary = latest_assistant_text[:4000]
        return update_task_record(
            record,
            loop_status=loop_status,
            summary=summary,
            executive_analysis=executive_analysis,
        )

    def _record_event(self, record: LoopTaskRecord, event: dict[str, Any]) -> LoopTaskRecord:
        events = [dict(item) for item in record.events]
        events.append(dict(event))
        return update_task_record(record, events=events)

    def _load_task(self, task_id: str) -> LoopTaskRecord | None:
        for record in list_task_records():
            if record.task_id == task_id:
                return record
        return None

    def _should_stop(self, record: LoopTaskRecord) -> bool:
        status = str(record.status or "").strip().lower()
        return bool(record.stop_requested) or status in {"stopping", "stopped"} or record.task_id in self._stop_requests

    def _wait_for_prompt_completion_or_stop(
        self,
        task_id: str,
        discussion_id: str,
        *,
        poll_seconds: float = 0.5,
    ) -> bool:
        while True:
            record = self._load_task(task_id)
            if record is not None and self._should_stop(record):
                return False
            if wait_for_prompt_completion(discussion_id, timeout=poll_seconds):
                return True

    def _raise_system_exit_in_thread(self, thread: threading.Thread) -> bool:
        thread_id = thread.ident
        if thread_id is None:
            return False
        result = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(thread_id),
            ctypes.py_object(SystemExit),
        )
        if result == 0:
            return False
        if result > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), None)
            return False
        return True

    def _latest_loop_status(self, messages: list[dict[str, Any]]) -> dict[str, Any] | None:
        for message in reversed(messages):
            if str(message.get("role", "")).strip().lower() == "user":
                continue
            text = str(message.get("text") or "")
            status = _extract_loop_status(text)
            if status is not None:
                return status
        return None

    def _apply_runtime_overrides(self, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = str(payload.get("task_id") or "").strip()
        if task_id and task_id in self._stop_requests:
            status = str(payload.get("status") or "").strip().lower()
            if status in {"running", "stopping"}:
                payload = dict(payload)
                payload["status"] = "stopped"
                payload["stop_requested"] = True
                if not payload.get("completed_at"):
                    payload["completed_at"] = payload.get("updated_at")
        return payload


def _extract_loop_status(text: str) -> dict[str, Any] | None:
    match = _LOOP_STATUS_RE.findall(str(text or ""))
    if match:
        payload = match[-1].strip()
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def _format_checklist(checklist: list[dict[str, Any]]) -> str:
    if not checklist:
        return "- No explicit checklist was provided."
    lines: list[str] = []
    for index, item in enumerate(checklist, start=1):
        label = str(item.get("label") or item.get("title") or item.get("text") or f"Item {index}").strip()
        state = "done" if bool(item.get("done")) else "open"
        lines.append(f"- [{state}] {label}")
    return "\n".join(lines)


def _latest_assistant_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if str(message.get("role", "")).strip().lower() == "assistant":
            return str(message.get("text") or "").strip()
    return ""


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if not text else text


def _augment_checklist_for_verification(prompt: str, checklist: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prompt_text = str(prompt or "").lower()
    if "agent" not in prompt_text or "create" not in prompt_text:
        return checklist

    verification_label = "Verify requested agents exist with list_agents"
    if any(str(item.get("label") or "").strip().lower() == verification_label.lower() for item in checklist):
        return checklist

    checklist.append({"label": verification_label})
    return checklist


_runner: ApmatiaAgentLoopRunner | None = None


def get_agent_loop_runner() -> ApmatiaAgentLoopRunner:
    global _runner
    if _runner is None:
        _runner = ApmatiaAgentLoopRunner()
    return _runner
