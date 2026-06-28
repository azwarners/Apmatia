from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_FLOAT_RE = r"[-+]?\d+(?:\.\d+)?"


@dataclass(slots=True)
class LlamaServerTiming:
    tokens: int | None = None
    milliseconds: float | None = None
    tokens_per_second: float | None = None


@dataclass(slots=True)
class LlamaServerStatus:
    server_ready: bool = False
    server_url: str | None = None
    chat_format: str | None = None
    thinking_enabled: bool | None = None
    slots_idle: bool | None = None
    selected_slot_id: int | None = None
    current_task_id: int | None = None
    sampler_chain: str | None = None
    prompt_cache_prompts: int | None = None
    prompt_cache_mib: float | None = None
    prompt_cache_limit_mib: float | None = None
    prompt_cache_limit_tokens: int | None = None
    prompt_cache_est_tokens: int | None = None
    prompt_tokens_total: int | None = None
    prompt_processing_progress: float | None = None
    prompt_processing_n_tokens: int | None = None
    prompt_processing_batch_tokens: int | None = None
    prompt_processing_done_tokens: int | None = None
    prompt_eval: LlamaServerTiming = field(default_factory=LlamaServerTiming)
    eval: LlamaServerTiming = field(default_factory=LlamaServerTiming)
    total_time_ms: float | None = None
    total_tokens: int | None = None
    truncated: bool | None = None
    context_checkpoints: int | None = None
    context_checkpoint_total: int | None = None
    context_checkpoint_tokens: int | None = None
    context_checkpoint_size_mib: float | None = None
    last_http_method: str | None = None
    last_http_path: str | None = None
    last_http_status: int | None = None
    raw_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["prompt_eval"] = asdict(self.prompt_eval)
        payload["eval"] = asdict(self.eval)
        return payload


def parse_llama_server_log_text(text: str) -> LlamaServerStatus:
    status = LlamaServerStatus()
    lines = [_ANSI_RE.sub("", line).strip() for line in str(text or "").splitlines()]
    status.raw_lines = [line for line in lines if line]

    for line in status.raw_lines:
        if "main: server is listening on http://" in line:
            status.server_ready = True
            match = re.search(r"(https?://\S+)", line)
            if match:
                status.server_url = match.group(1).rstrip(".")
            continue

        if "srv update_slots: all slots are idle" in line:
            status.slots_idle = True
            continue

        match = re.search(r"srv  params_from_: Chat format:\s*(.+)$", line)
        if match:
            status.chat_format = match.group(1).strip()
            continue

        match = re.search(r"thinking\s*=\s*(\d+)", line)
        if "chat template" in line and match:
            status.thinking_enabled = bool(int(match.group(1)))
            continue

        match = re.search(
            r"slot\s+launch_slot_:\s+id\s+(?P<slot>\d+)\s+\|\s+task\s+(?P<task>-?\d+)\s+\|\s+sampler chain:\s*(?P<chain>.+)$",
            line,
        )
        if match:
            status.selected_slot_id = int(match.group("slot"))
            status.current_task_id = int(match.group("task"))
            status.sampler_chain = match.group("chain").strip()
            status.slots_idle = False
            continue

        match = re.search(
            r"slot\s+launch_slot_:\s+id\s+(?P<slot>\d+)\s+\|\s+task\s+(?P<task>-?\d+)\s+\|\s+processing task, is_child = (?P<child>\d+)",
            line,
        )
        if match:
            status.selected_slot_id = int(match.group("slot"))
            status.current_task_id = int(match.group("task"))
            status.slots_idle = False
            continue

        match = re.search(
            r"slot\s+update_slots:\s+id\s+(?P<slot>\d+)\s+\|\s+task\s+(?P<task>-?\d+)\s+\|\s+new prompt, n_ctx_slot = (?P<n_ctx>\d+), n_keep = (?P<n_keep>\d+), task.n_tokens = (?P<tokens>\d+)",
            line,
        )
        if match:
            status.selected_slot_id = int(match.group("slot"))
            status.current_task_id = int(match.group("task"))
            status.prompt_tokens_total = int(match.group("tokens"))
            status.slots_idle = False
            continue

        match = re.search(
            r"slot\s+update_slots:\s+id\s+(?P<slot>\d+)\s+\|\s+task\s+(?P<task>-?\d+)\s+\|\s+prompt processing progress, n_tokens = (?P<n_tokens>\d+), batch\.n_tokens = (?P<batch>\d+), progress = (?P<progress>{float})".format(
                float=_FLOAT_RE
            ),
            line,
        )
        if match:
            status.selected_slot_id = int(match.group("slot"))
            status.current_task_id = int(match.group("task"))
            status.prompt_processing_n_tokens = int(match.group("n_tokens"))
            status.prompt_processing_batch_tokens = int(match.group("batch"))
            status.prompt_processing_progress = float(match.group("progress"))
            status.slots_idle = False
            continue

        match = re.search(
            r"slot\s+init_sampler:\s+id\s+(?P<slot>\d+)\s+\|\s+task\s+(?P<task>-?\d+)\s+\|\s+init sampler, took (?P<ms>{float}) ms, tokens: text = (?P<text>\d+), total = (?P<total>\d+)".format(
                float=_FLOAT_RE
            ),
            line,
        )
        if match:
            status.selected_slot_id = int(match.group("slot"))
            status.current_task_id = int(match.group("task"))
            status.prompt_eval = LlamaServerTiming(
                tokens=int(match.group("total")),
                milliseconds=float(match.group("ms")),
                tokens_per_second=(
                    int(match.group("total")) / (float(match.group("ms")) / 1000.0)
                    if float(match.group("ms")) > 0
                    else None
                ),
            )
            status.slots_idle = False
            continue

        match = re.search(
            r"slot\s+update_slots:\s+id\s+(?P<slot>\d+)\s+\|\s+task\s+(?P<task>-?\d+)\s+\|\s+prompt processing done, n_tokens = (?P<tokens>\d+), batch\.n_tokens = (?P<batch>\d+)",
            line,
        )
        if match:
            status.selected_slot_id = int(match.group("slot"))
            status.current_task_id = int(match.group("task"))
            status.prompt_processing_done_tokens = int(match.group("tokens"))
            status.slots_idle = False
            continue

        match = re.search(
            r"slot\s+create_check:\s+id\s+(?P<slot>\d+)\s+\|\s+task\s+(?P<task>-?\d+)\s+\|\s+created context checkpoint (?P<index>\d+) of (?P<total>\d+) \(pos_min = (?P<pos_min>\d+), pos_max = (?P<pos_max>\d+), n_tokens = (?P<tokens>\d+), size = (?P<size>{float}) MiB\)".format(
                float=_FLOAT_RE
            ),
            line,
        )
        if match:
            status.selected_slot_id = int(match.group("slot"))
            status.current_task_id = int(match.group("task"))
            status.context_checkpoints = int(match.group("index"))
            status.context_checkpoint_total = int(match.group("total"))
            status.context_checkpoint_tokens = int(match.group("tokens"))
            status.context_checkpoint_size_mib = float(match.group("size"))
            status.slots_idle = False
            continue

        match = re.search(
            r"srv\s+update:\s+- cache state:\s+(?P<prompts>\d+) prompts, (?P<mib>{float}) MiB \(limits: (?P<limit_mib>{float}) MiB, (?P<limit_tokens>\d+) tokens, (?P<est>\d+) est\)".format(
                float=_FLOAT_RE
            ),
            line,
        )
        if match:
            status.prompt_cache_prompts = int(match.group("prompts"))
            status.prompt_cache_mib = float(match.group("mib"))
            status.prompt_cache_limit_mib = float(match.group("limit_mib"))
            status.prompt_cache_limit_tokens = int(match.group("limit_tokens"))
            status.prompt_cache_est_tokens = int(match.group("est"))
            continue

        match = re.search(
            r"srv\s+log_server_r:\s+done request:\s+(?P<method>\S+)\s+(?P<path>\S+)\s+\S+\s+(?P<status>\d+)",
            line,
        )
        if match:
            status.last_http_method = match.group("method")
            status.last_http_path = match.group("path")
            status.last_http_status = int(match.group("status"))
            continue

        match = re.search(
            r"prompt eval time =\s+(?P<ms>{float}) ms / +(?P<tokens>\d+) tokens .*?(?P<tps>{float}) tokens per second".format(
                float=_FLOAT_RE
            ),
            line,
        )
        if match:
            status.prompt_eval = LlamaServerTiming(
                tokens=int(match.group("tokens")),
                milliseconds=float(match.group("ms")),
                tokens_per_second=float(match.group("tps")),
            )
            continue

        match = re.search(
            r"eval time =\s+(?P<ms>{float}) ms / +(?P<tokens>\d+) tokens .*?(?P<tps>{float}) tokens per second".format(
                float=_FLOAT_RE
            ),
            line,
        )
        if match:
            status.eval = LlamaServerTiming(
                tokens=int(match.group("tokens")),
                milliseconds=float(match.group("ms")),
                tokens_per_second=float(match.group("tps")),
            )
            continue

        match = re.search(
            r"total time =\s+(?P<ms>{float}) ms / +(?P<tokens>\d+) tokens".format(float=_FLOAT_RE),
            line,
        )
        if match:
            status.total_time_ms = float(match.group("ms"))
            status.total_tokens = int(match.group("tokens"))
            continue

        match = re.search(
            r"slot\s+release:\s+id\s+(?P<slot>\d+)\s+\|\s+task\s+(?P<task>-?\d+)\s+\|\s+stop processing: n_tokens = (?P<tokens>\d+), truncated = (?P<truncated>\d+)",
            line,
        )
        if match:
            status.selected_slot_id = int(match.group("slot"))
            status.total_tokens = int(match.group("tokens"))
            status.truncated = bool(int(match.group("truncated")))
            continue

    return status


def parse_llama_server_log_file(path: str | Path) -> LlamaServerStatus | None:
    file_path = _resolve_llama_server_log_path(path)
    if not file_path.exists():
        return None
    return parse_llama_server_log_text(file_path.read_text(encoding="utf-8", errors="replace"))


def _resolve_llama_server_log_path(path: str | Path) -> Path:
    file_path = Path(path).expanduser()
    if file_path.is_dir():
        candidates = [
            candidate
            for candidate in file_path.iterdir()
            if candidate.is_file() and not candidate.name.startswith(".")
        ]
        if not candidates:
            return file_path
        return max(candidates, key=lambda candidate: (candidate.stat().st_mtime, candidate.name))
    return file_path


def parse_llama_server_log_turns(text: str) -> list[LlamaServerStatus]:
    lines = [_ANSI_RE.sub("", line).strip() for line in str(text or "").splitlines()]
    blocks: list[list[str]] = []
    current_block: list[str] = []
    for line in lines:
        if not line:
            continue
        current_block.append(line)
        if "slot      release:" in line:
            blocks.append(current_block)
            current_block = []

    turns: list[LlamaServerStatus] = []
    for block in blocks:
        status = parse_llama_server_log_text("\n".join(block))
        if (
            status.prompt_eval.tokens is not None
            or status.eval.tokens is not None
            or status.total_time_ms is not None
            or status.prompt_processing_progress is not None
        ):
            turns.append(status)
    return turns


def summarize_llama_server_status(status: LlamaServerStatus | dict[str, Any] | None) -> str | None:
    if status is None:
        return None
    payload = status.to_dict() if isinstance(status, LlamaServerStatus) else dict(status)
    pieces: list[str] = []

    chat_format = payload.get("chat_format")
    if chat_format:
        pieces.append(f"chat format {chat_format}")

    if payload.get("thinking_enabled") is True:
        pieces.append("thinking on")
    elif payload.get("thinking_enabled") is False:
        pieces.append("thinking off")

    prompt_progress = payload.get("prompt_processing_progress")
    task_id = payload.get("current_task_id")
    slot_id = payload.get("selected_slot_id")
    if slot_id is not None and task_id is not None:
        pieces.append(f"slot {slot_id} task {task_id}")
    elif slot_id is not None:
        pieces.append(f"slot {slot_id}")

    if prompt_progress is not None:
        prompt_tokens = payload.get("prompt_processing_n_tokens") or payload.get("prompt_processing_done_tokens")
        total_tokens = payload.get("prompt_tokens_total")
        progress_bits: list[str] = []
        if prompt_progress is not None:
            progress_bits.append(f"{float(prompt_progress) * 100:.1f}%")
        if prompt_tokens is not None and total_tokens is not None:
            progress_bits.append(f"{prompt_tokens}/{total_tokens} prompt tokens")
        elif prompt_tokens is not None:
            progress_bits.append(f"{prompt_tokens} prompt tokens")
        if progress_bits:
            pieces.append("prompt " + ", ".join(progress_bits))

    prompt_eval = payload.get("prompt_eval") or {}
    if isinstance(prompt_eval, dict) and prompt_eval.get("tokens_per_second") is not None:
        pieces.append(
            "prompt eval "
            f"{float(prompt_eval.get('tokens_per_second')):.2f} tok/s"
        )

    eval_stats = payload.get("eval") or {}
    if isinstance(eval_stats, dict) and eval_stats.get("tokens_per_second") is not None:
        pieces.append(f"generation {float(eval_stats['tokens_per_second']):.2f} tok/s")

    total_tokens = payload.get("total_tokens")
    total_time_ms = payload.get("total_time_ms")
    if total_tokens is not None and total_time_ms is not None:
        pieces.append(f"total {int(total_tokens)} tokens / {float(total_time_ms) / 1000.0:.2f}s")

    if payload.get("slots_idle") is True:
        pieces.append("idle")

    return ", ".join(pieces) if pieces else None
