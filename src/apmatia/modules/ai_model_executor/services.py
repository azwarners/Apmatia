from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from apmatia.core.app_config import get_config_value, load_app_config, save_app_config
from apmatia.core.runtime_paths import get_app_dir
from apmatia.lib.apmatia_core.models import utc_now

from apmatia.modules.ai_model_manager import AIModelManager, GGUFModelRecord

from .models import HostResourceSnapshot, LlamaCppRuntimeConfig, ModelExecutionRecord

_EXECUTIONS_KEY = ("ai_model_executor", "executions")
_RUNTIME_CONFIG_KEY = ("ai_model_executor", "runtime_config")


def _parse_int(value: Any, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _parse_tuple(value: Any) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return tuple(part.strip() for part in str(value).split() if part.strip())


def _normalize_runtime_config(item: dict[str, Any]) -> dict[str, Any]:
    data = dict(item)
    data["runtime_id"] = _parse_text(data.get("runtime_id"), default="llama_cpp")
    data["executable_path"] = _parse_text(data.get("executable_path"), default="llama-server")
    data["default_args"] = _parse_tuple(data.get("default_args"))
    data["host"] = _parse_text(data.get("host"), default="127.0.0.1")
    data["default_port"] = _parse_int(data.get("default_port"), default=8000) or 8000
    data["stop_conflicting_models"] = bool(data.get("stop_conflicting_models", True))
    data["log_dir"] = _parse_text(data.get("log_dir"))
    return data


def _normalize_execution_record(item: dict[str, Any]) -> dict[str, Any]:
    data = dict(item)
    data["id"] = _parse_int(data.get("id"))
    data["owner_user_id"] = _parse_int(data.get("owner_user_id"))
    data["owner_group_id"] = _parse_int(data.get("owner_group_id"))
    data["mode"] = _parse_int(data.get("mode"), default=0) or 0
    data["created_at"] = _parse_datetime(data.get("created_at"))
    data["updated_at"] = _parse_datetime(data.get("updated_at"))
    data["model_id"] = _parse_int(data.get("model_id"), default=0) or 0
    data["host_id"] = _parse_text(data.get("host_id"), default="local")
    data["runtime_id"] = _parse_text(data.get("runtime_id"), default="llama_cpp")
    data["pid"] = _parse_int(data.get("pid"))
    data["port"] = _parse_int(data.get("port"))
    data["endpoint_url"] = _parse_text(data.get("endpoint_url"))
    data["status"] = _parse_text(data.get("status"), default="stopped")
    data["launch_command"] = _parse_text(data.get("launch_command"))
    data["log_path"] = _parse_text(data.get("log_path"))
    metadata = data.get("metadata")
    data["metadata"] = dict(metadata) if isinstance(metadata, dict) else {}
    return data


def _serialize_runtime_config(record: LlamaCppRuntimeConfig | dict[str, Any]) -> dict[str, Any]:
    data = record if isinstance(record, dict) else asdict(record)
    normalized = _normalize_runtime_config(dict(data))
    return {
        "runtime_id": normalized["runtime_id"],
        "executable_path": normalized["executable_path"],
        "default_args": list(normalized["default_args"]),
        "host": normalized["host"],
        "default_port": normalized["default_port"],
        "stop_conflicting_models": normalized["stop_conflicting_models"],
        "log_dir": normalized["log_dir"],
    }


def _serialize_execution_record(record: ModelExecutionRecord | dict[str, Any]) -> dict[str, Any]:
    data = record if isinstance(record, dict) else asdict(record)
    normalized = _normalize_execution_record(dict(data))
    return {
        "id": normalized["id"],
        "owner_user_id": normalized["owner_user_id"],
        "owner_group_id": normalized["owner_group_id"],
        "mode": normalized["mode"],
        "created_at": normalized["created_at"].isoformat(),
        "updated_at": normalized["updated_at"].isoformat(),
        "model_id": normalized["model_id"],
        "host_id": normalized["host_id"],
        "runtime_id": normalized["runtime_id"],
        "pid": normalized["pid"],
        "port": normalized["port"],
        "endpoint_url": normalized["endpoint_url"],
        "status": normalized["status"],
        "launch_command": normalized["launch_command"],
        "log_path": normalized["log_path"],
        "metadata": dict(normalized["metadata"]),
    }


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if not value:
        return utc_now()
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return utc_now()
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _load_runtime_config() -> dict[str, Any]:
    config = get_config_value(*_RUNTIME_CONFIG_KEY, default={})
    if not isinstance(config, dict):
        return _serialize_runtime_config(LlamaCppRuntimeConfig())
    return _normalize_runtime_config(dict(config))


def get_runtime_config() -> LlamaCppRuntimeConfig:
    return LlamaCppRuntimeConfig(**_load_runtime_config())


def save_runtime_config(config: LlamaCppRuntimeConfig | dict[str, Any]) -> LlamaCppRuntimeConfig:
    normalized = _normalize_runtime_config(config if isinstance(config, dict) else asdict(config))
    app_config = load_app_config()
    app_config.setdefault("ai_model_executor", {})
    app_config["ai_model_executor"]["runtime_config"] = _serialize_runtime_config(normalized)
    save_app_config(app_config)
    return LlamaCppRuntimeConfig(**normalized)


def _load_execution_items() -> list[dict[str, Any]]:
    records = get_config_value(*_EXECUTIONS_KEY, default=[])
    if not isinstance(records, list):
        return []
    return [_normalize_execution_record(dict(item)) for item in records if isinstance(item, dict)]


def _save_execution_items(items: list[dict[str, Any]]) -> None:
    app_config = load_app_config()
    app_config.setdefault("ai_model_executor", {})
    app_config["ai_model_executor"]["executions"] = [
        _serialize_execution_record(item if isinstance(item, dict) else dict(item))
        for item in items
    ]
    save_app_config(app_config)


def _manager() -> AIModelManager:
    return AIModelManager()


def list_execution_records(*, model_id: int | None = None) -> list[ModelExecutionRecord]:
    records = [ModelExecutionRecord(**item) for item in _load_execution_items()]
    if model_id is None:
        return sorted(records, key=lambda item: (str(item.host_id).lower(), int(item.id or 0)))
    return [record for record in records if int(record.model_id) == int(model_id)]


def get_execution_record(execution_id: int) -> ModelExecutionRecord | None:
    for record in list_execution_records():
        if int(record.id or -1) == int(execution_id):
            return record
    return None


def inspect_host_resources() -> HostResourceSnapshot:
    ram_total_bytes, ram_available_bytes = _inspect_system_ram()
    vram_total_bytes, vram_available_bytes, gpu_count, metadata = _inspect_vram()
    return HostResourceSnapshot(
        ram_total_bytes=ram_total_bytes,
        ram_available_bytes=ram_available_bytes,
        vram_total_bytes=vram_total_bytes,
        vram_available_bytes=vram_available_bytes,
        gpu_count=gpu_count,
        source="local",
        metadata=metadata,
    )


def can_run_model(model_id: int, *, resources: HostResourceSnapshot | dict[str, Any] | None = None) -> dict[str, Any]:
    model = _require_model(model_id)
    snapshot = _coerce_resources(resources) if resources is not None else inspect_host_resources()
    reasons: list[str] = []
    ram_required = int(model.estimated_ram_bytes or 0)
    vram_required = int(model.estimated_vram_bytes or 0)

    if snapshot.ram_total_bytes == 0 and snapshot.vram_total_bytes == 0:
        reasons.append("Host resources unavailable.")
    if ram_required and snapshot.ram_available_bytes < ram_required:
        reasons.append("Not enough available RAM.")
    if vram_required and snapshot.vram_available_bytes < vram_required:
        reasons.append("Not enough available VRAM.")

    return {
        "can_run": not reasons,
        "reasons": reasons,
        "model": _model_to_dict(model),
        "resources": _resources_to_dict(snapshot),
        "required_ram_bytes": ram_required,
        "required_vram_bytes": vram_required,
        "available_ram_bytes": snapshot.ram_available_bytes,
        "available_vram_bytes": snapshot.vram_available_bytes,
    }


def start_model(
    model_id: int,
    *,
    host_id: str = "local",
    runtime_id: str | None = None,
    port: int | None = None,
    stop_conflicting_models: bool | None = None,
    launch_args: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    model = _require_model(model_id)
    runtime = get_runtime_config()
    effective_runtime_id = runtime_id or runtime.runtime_id
    effective_stop_conflicts = runtime.stop_conflicting_models if stop_conflicting_models is None else bool(stop_conflicting_models)
    effective_port = int(port or runtime.default_port)
    feasibility = can_run_model(model_id)
    if not feasibility["can_run"]:
        raise ValueError("; ".join(feasibility["reasons"]) or "Model cannot run on the current host.")

    stopped: list[dict[str, Any]] = []
    if effective_stop_conflicts:
        stopped = stop_conflicting_models_for_host(host_id=host_id, runtime_id=effective_runtime_id, port=effective_port)

    command = _build_launch_command(
        model,
        runtime,
        port=effective_port,
        extra_args=launch_args or (),
    )
    log_path = _allocate_log_path(model, host_id=host_id, runtime_id=effective_runtime_id)
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    log_handle = open(log_path, "a", encoding="utf-8")
    try:
        process = subprocess.Popen(command, stdout=log_handle, stderr=subprocess.STDOUT)
    except Exception:
        log_handle.close()
        raise
    log_handle.close()

    record = _create_execution_record(
        model_id=model_id,
        host_id=host_id,
        runtime_id=effective_runtime_id,
        pid=process.pid,
        port=effective_port,
        endpoint_url=_build_endpoint_url(runtime.host, effective_port),
        status="running",
        launch_command=shlex.join(command),
        log_path=log_path,
        metadata={"launch": "llama.cpp"},
    )
    items = _load_execution_items()
    items.append(_serialize_execution_record(record))
    _save_execution_items(items)
    return {
        "status": "running",
        "execution": _execution_to_dict(record),
        "stopped_conflicts": stopped,
        "can_run": feasibility,
    }


def stop_model(
    model_id: int | None = None,
    *,
    execution_id: int | None = None,
    host_id: str = "local",
    runtime_id: str | None = None,
) -> dict[str, Any]:
    record = _find_active_execution(model_id=model_id, execution_id=execution_id, host_id=host_id, runtime_id=runtime_id)
    if record is None:
        return {"status": "not_found", "stopped": False}

    if record.pid is not None:
        try:
            os.kill(int(record.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass

    updated = replace(record, status="stopped", updated_at=utc_now())
    _replace_execution_record(updated)
    return {"status": "stopped", "stopped": True, "execution": _execution_to_dict(updated)}


def stop_conflicting_models_for_host(
    *,
    host_id: str,
    runtime_id: str,
    port: int | None = None,
) -> list[dict[str, Any]]:
    stopped: list[dict[str, Any]] = []
    for record in list_execution_records():
        if str(record.status).lower() != "running":
            continue
        if str(record.host_id) != str(host_id):
            continue
        if str(record.runtime_id) != str(runtime_id):
            continue
        result = stop_model(execution_id=int(record.id), host_id=host_id, runtime_id=runtime_id)
        if result.get("stopped"):
            stopped.append(result["execution"])
    return stopped


def get_execution_status(*, model_id: int | None = None) -> dict[str, Any]:
    records = list_execution_records(model_id=model_id)
    return {
        "items": [_execution_to_dict(record) for record in records],
        "count": len(records),
        "model_id": model_id,
    }


def update_runtime_config(**updates: Any) -> dict[str, Any]:
    config = get_runtime_config()
    merged = replace(
        config,
        runtime_id=_parse_text(updates.get("runtime_id"), default=config.runtime_id) if "runtime_id" in updates else config.runtime_id,
        executable_path=_parse_text(updates.get("executable_path"), default=config.executable_path)
        if "executable_path" in updates
        else config.executable_path,
        default_args=_parse_tuple(updates.get("default_args")) if "default_args" in updates else config.default_args,
        host=_parse_text(updates.get("host"), default=config.host) if "host" in updates else config.host,
        default_port=(
            _parse_int(updates.get("default_port"), default=config.default_port) or config.default_port
            if "default_port" in updates
            else config.default_port
        ),
        stop_conflicting_models=
        bool(updates.get("stop_conflicting_models", config.stop_conflicting_models))
        if "stop_conflicting_models" in updates
        else config.stop_conflicting_models,
        log_dir=_parse_text(updates.get("log_dir"), default=config.log_dir) if "log_dir" in updates else config.log_dir,
    )
    return _runtime_to_dict(save_runtime_config(merged))


def _require_model(model_id: int) -> GGUFModelRecord:
    model = _manager().get_model(model_id)
    if model is None:
        raise ValueError(f"GGUF model not found: {model_id}")
    return model


def _build_launch_command(
    model: GGUFModelRecord,
    runtime: LlamaCppRuntimeConfig,
    *,
    port: int,
    extra_args: Iterable[str],
) -> list[str]:
    command = [
        runtime.executable_path,
        *runtime.default_args,
        "--model",
        str(_resolve_launch_path(model.local_path)),
        "--host",
        runtime.host,
        "--port",
        str(port),
    ]
    command.extend(str(arg) for arg in extra_args if str(arg).strip())
    return command


def _build_endpoint_url(host: str, port: int) -> str:
    return f"http://{host}:{int(port)}"


def _allocate_log_path(model: GGUFModelRecord, *, host_id: str, runtime_id: str) -> str:
    runtime = get_runtime_config()
    base_dir = Path(runtime.log_dir) if runtime.log_dir else get_app_dir() / "logs" / "ai_model_executor"
    timestamp = utc_now().strftime("%Y%m%dT%H%M%S")
    safe_model_id = int(model.id or 0)
    return str(base_dir / f"{host_id}-{runtime_id}-{safe_model_id}-{timestamp}.log")


def _create_execution_record(
    *,
    model_id: int,
    host_id: str,
    runtime_id: str,
    pid: int | None,
    port: int | None,
    endpoint_url: str,
    status: str,
    launch_command: str,
    log_path: str,
    metadata: dict[str, Any] | None = None,
) -> ModelExecutionRecord:
    items = _load_execution_items()
    next_id = max((int(item.get("id", 0)) for item in items), default=0) + 1
    now = utc_now()
    return ModelExecutionRecord(
        id=next_id,
        model_id=model_id,
        host_id=host_id,
        runtime_id=runtime_id,
        pid=pid,
        port=port,
        endpoint_url=endpoint_url,
        status=status,
        launch_command=launch_command,
        log_path=log_path,
        metadata=dict(metadata or {}),
        created_at=now,
        updated_at=now,
    )


def _replace_execution_record(record: ModelExecutionRecord) -> None:
    items = _load_execution_items()
    for index, item in enumerate(items):
        if int(item.get("id", -1)) != int(record.id or -1):
            continue
        items[index] = _serialize_execution_record(record)
        _save_execution_items(items)
        return
    items.append(_serialize_execution_record(record))
    _save_execution_items(items)


def _find_active_execution(
    *,
    model_id: int | None = None,
    execution_id: int | None = None,
    host_id: str = "local",
    runtime_id: str | None = None,
) -> ModelExecutionRecord | None:
    records = list_execution_records()
    if execution_id is not None:
        for record in records:
            if int(record.id or -1) == int(execution_id):
                return record
        return None
    candidates = [record for record in records if str(record.status).lower() == "running" and str(record.host_id) == str(host_id)]
    if runtime_id is not None:
        candidates = [record for record in candidates if str(record.runtime_id) == str(runtime_id)]
    if model_id is not None:
        candidates = [record for record in candidates if int(record.model_id) == int(model_id)]
    return candidates[-1] if candidates else None


def _inspect_system_ram() -> tuple[int, int]:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return 0, 0
    total_kib = 0
    available_kib = 0
    with meminfo.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("MemTotal:"):
                total_kib = _parse_meminfo_value(line)
            elif line.startswith("MemAvailable:"):
                available_kib = _parse_meminfo_value(line)
            elif line.startswith("MemFree:") and available_kib == 0:
                available_kib = _parse_meminfo_value(line)
    return total_kib * 1024, available_kib * 1024


def _parse_meminfo_value(line: str) -> int:
    parts = line.split()
    if len(parts) < 2:
        return 0
    try:
        return int(parts[1])
    except ValueError:
        return 0


def _inspect_vram() -> tuple[int, int, int, dict[str, Any]]:
    command = [
        "nvidia-smi",
        "--query-gpu=memory.total,memory.free",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
    except Exception:
        return 0, 0, 0, {"available": False, "devices": []}

    total_bytes = 0
    free_bytes = 0
    devices: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        values = [part.strip() for part in line.split(",") if part.strip()]
        if len(values) < 2:
            continue
        try:
            total_mib = int(float(values[0]))
            free_mib = int(float(values[1]))
        except ValueError:
            continue
        total_bytes += total_mib * 1024 * 1024
        free_bytes += free_mib * 1024 * 1024
        devices.append({"total_bytes": total_mib * 1024 * 1024, "free_bytes": free_mib * 1024 * 1024})
    return total_bytes, free_bytes, len(devices), {"available": True, "devices": devices}


def _coerce_resources(resources: HostResourceSnapshot | dict[str, Any]) -> HostResourceSnapshot:
    if isinstance(resources, HostResourceSnapshot):
        return resources
    return HostResourceSnapshot(
        ram_total_bytes=_parse_int(resources.get("ram_total_bytes"), default=0) or 0,
        ram_available_bytes=_parse_int(resources.get("ram_available_bytes"), default=0) or 0,
        vram_total_bytes=_parse_int(resources.get("vram_total_bytes"), default=0) or 0,
        vram_available_bytes=_parse_int(resources.get("vram_available_bytes"), default=0) or 0,
        gpu_count=_parse_int(resources.get("gpu_count"), default=0) or 0,
        source=_parse_text(resources.get("source"), default="manual"),
        metadata=dict(resources.get("metadata") or {}) if isinstance(resources.get("metadata"), dict) else {},
    )


def _resources_to_dict(snapshot: HostResourceSnapshot) -> dict[str, Any]:
    return {
        "ram_total_bytes": snapshot.ram_total_bytes,
        "ram_available_bytes": snapshot.ram_available_bytes,
        "vram_total_bytes": snapshot.vram_total_bytes,
        "vram_available_bytes": snapshot.vram_available_bytes,
        "gpu_count": snapshot.gpu_count,
        "source": snapshot.source,
        "metadata": dict(snapshot.metadata),
    }


def _runtime_to_dict(config: LlamaCppRuntimeConfig) -> dict[str, Any]:
    return {
        "runtime_id": config.runtime_id,
        "executable_path": config.executable_path,
        "default_args": list(config.default_args),
        "host": config.host,
        "default_port": config.default_port,
        "stop_conflicting_models": config.stop_conflicting_models,
        "log_dir": config.log_dir,
    }


def _model_to_dict(model: GGUFModelRecord) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "local_path": model.local_path,
        "estimated_ram_bytes": model.estimated_ram_bytes,
        "estimated_vram_bytes": model.estimated_vram_bytes,
        "size_class": model.size_class,
        "cost_mode": model.cost_mode,
        "metadata": dict(model.metadata),
    }


def _execution_to_dict(record: ModelExecutionRecord) -> dict[str, Any]:
    return _serialize_execution_record(record)


def _resolve_launch_path(local_path: str) -> Path:
    path = Path(local_path).expanduser()
    if path.is_file():
        return path.resolve()
    if path.is_dir():
        matches = sorted(
            (p for p in path.rglob("*") if p.is_file() and p.suffix.lower() == ".gguf"),
            key=lambda item: str(item).lower(),
        )
        if matches:
            return matches[0].resolve()
    raise ValueError(f"No GGUF file found at path: {local_path}")


# ---------------------------------------------------------------------------
# Queue, Reservation, Capacity, and Runtime helpers for the view layer
# ---------------------------------------------------------------------------

_QUEUE_KEY = ("ai_model_executor", "queue")
_RESERVATIONS_KEY = ("ai_model_executor", "reservations")
_LEASES_KEY = ("ai_model_executor", "leases")
_RUNTIMES_KEY = ("ai_model_executor", "runtimes")


def _load_queue_items() -> list[dict[str, Any]]:
    items = get_config_value(*_QUEUE_KEY, default=[])
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items]


def _save_queue_items(items: list[dict[str, Any]]) -> None:
    app_config = load_app_config()
    app_config.setdefault("ai_model_executor", {})
    app_config["ai_model_executor"]["queue"] = items
    save_app_config(app_config)


def _load_reservations() -> list[dict[str, Any]]:
    items = get_config_value(*_RESERVATIONS_KEY, default=[])
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items]


def _save_reservations(items: list[dict[str, Any]]) -> None:
    app_config = load_app_config()
    app_config.setdefault("ai_model_executor", {})
    app_config["ai_model_executor"]["reservations"] = items
    save_app_config(app_config)


def _load_leases() -> list[dict[str, Any]]:
    items = get_config_value(*_LEASES_KEY, default=[])
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items]


def _save_leases(items: list[dict[str, Any]]) -> None:
    app_config = load_app_config()
    app_config.setdefault("ai_model_executor", {})
    app_config["ai_model_executor"]["leases"] = items
    save_app_config(app_config)


def _load_runtimes() -> list[dict[str, Any]]:
    items = get_config_value(*_RUNTIMES_KEY, default=[])
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items]


def _save_runtimes(items: list[dict[str, Any]]) -> None:
    app_config = load_app_config()
    app_config.setdefault("ai_model_executor", {})
    app_config["ai_model_executor"]["runtimes"] = items
    save_app_config(app_config)


def list_runtimes() -> list[dict[str, Any]]:
    runtimes = _load_runtimes()
    # Auto-register known runtimes from config
    runtime_config = get_runtime_config()
    existing_ids = {r.get("id") for r in runtimes}
    if runtime_config.runtime_id not in existing_ids:
        runtimes.append({
            "id": runtime_config.runtime_id,
            "name": runtime_config.executable_path,
            "max_concurrency": 1,
            "endpoint_url": "",
            "state": "available",
        })
    return runtimes


def enqueue_work(
    *,
    model_id: int,
    prompt: str,
    priority: int = 0,
    runtime_id: str = "",
    system_prompt: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    from datetime import datetime, timezone
    items = _load_queue_items()
    next_id = max((int(item.get("id", 0)) for item in items), default=0) + 1
    item = {
        "id": next_id,
        "model_id": model_id,
        "prompt": prompt,
        "system_prompt": system_prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "priority": priority,
        "runtime_id": runtime_id or "",
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claimed_at": None,
        "completed_at": None,
        "error": None,
    }
    items.append(item)
    _save_queue_items(items)
    return {"status": "enqueued", "item": item}


def cancel_queue_item(item_id: str) -> dict[str, Any]:
    items = _load_queue_items()
    for item in items:
        if str(item.get("id")) == str(item_id):
            item["status"] = "cancelled"
            _save_queue_items(items)
            return {"status": "cancelled", "item": item}
    return {"status": "not_found", "item_id": item_id}


def request_reservation(
    *,
    runtime_id: str,
    owner_user_id: int,
    owner_session_id: str,
    requested_seats: int = 1,
    mode: str = "shared",
) -> dict[str, Any]:
    from datetime import datetime, timezone
    items = _load_reservations()
    next_id = f"res_{int(datetime.now(timezone.utc).timestamp())}"
    item = {
        "id": next_id,
        "runtime_id": runtime_id,
        "owner_user_id": owner_user_id,
        "owner_session_id": owner_session_id,
        "requested_seats": requested_seats,
        "mode": mode,
        "state": "requested",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "activated_at": None,
        "released_at": None,
    }
    items.append(item)
    _save_reservations(items)
    return {"status": "created", "reservation": item}


def release_reservation(reservation_id: str) -> dict[str, Any]:
    items = _load_reservations()
    for item in items:
        if str(item.get("id")) == str(reservation_id):
            item["state"] = "released"
            _save_reservations(items)
            return {"status": "released", "reservation": item}
    return {"status": "not_found", "reservation_id": reservation_id}
