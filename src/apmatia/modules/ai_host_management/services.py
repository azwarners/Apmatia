from __future__ import annotations

from dataclasses import asdict, replace
import base64
import errno
from datetime import datetime, timezone
import pty
import os
from pathlib import Path
import re
import select
import subprocess
import shutil
from typing import Any, Mapping

from apmatia.core.app_config import get_config_value, load_app_config, save_app_config
from apmatia.core.models import utc_now

from .models import AIHost, AIHostResourceReport, HostResourceSnapshot

_HOSTS_KEY = ("ai_host_management", "hosts")
_DEFAULT_SSH_KEY_PATH = "~/.apmatia/ssh/id_ed25519"
_SUPPORTED_CONNECTION_TYPES = {"local", "ssh"}
_UNSUPPORTED_SECRET_KEYS = {
    "password",
    "passphrase",
    "private_key",
    "private_key_pem",
    "secret",
    "token",
    "ssh_password",
    "sudo_password",
}
_REMOTE_GPU_MARKER = "__APMATIA_GPU_START__"
_SSH_KNOWN_HOSTS_FILE = "/tmp/apmatia_known_hosts"


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _parse_int(value: Any, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    return default


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


def _reject_sensitive_fields(payload: Mapping[str, Any]) -> None:
    lowered = {str(key).strip().lower() for key in payload}
    forbidden = sorted(field for field in lowered if field in _UNSUPPORTED_SECRET_KEYS)
    if forbidden:
        names = ", ".join(forbidden)
        raise ValueError(
            f"Plaintext password or secret fields are not supported. Use credential_ref instead. Unsupported fields: {names}"
        )


def _normalize_host_record(item: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(item)
    data["id"] = _parse_int(data.get("id"))
    data["name"] = _normalize_text(data.get("name"))
    data["hostname"] = _normalize_text(data.get("hostname"))
    data["role"] = _normalize_text(data.get("role"))
    data["connection_type"] = _normalize_text(data.get("connection_type") or "local").lower() or "local"
    data["username"] = _normalize_text(data.get("username"))
    data["port"] = _parse_int(data.get("port"), default=22) or 22
    data["credential_ref"] = _normalize_text(data.get("credential_ref"))
    data["enabled"] = _parse_bool(data.get("enabled"), default=True)
    data["notes"] = _normalize_text(data.get("notes"))
    data["created_at"] = _parse_datetime(data.get("created_at"))
    data["updated_at"] = _parse_datetime(data.get("updated_at"))
    return data


def _serialize_host_record(record: AIHost | Mapping[str, Any]) -> dict[str, Any]:
    data = record if isinstance(record, Mapping) else asdict(record)
    normalized = _normalize_host_record(data)
    return {
        "id": normalized["id"],
        "name": normalized["name"],
        "hostname": normalized["hostname"],
        "role": normalized["role"],
        "connection_type": normalized["connection_type"],
        "username": normalized["username"],
        "port": normalized["port"],
        "credential_ref": normalized["credential_ref"],
        "enabled": normalized["enabled"],
        "notes": normalized["notes"],
        "created_at": normalized["created_at"].isoformat(),
        "updated_at": normalized["updated_at"].isoformat(),
    }


def _load_host_items() -> list[dict[str, Any]]:
    hosts = get_config_value(*_HOSTS_KEY, default=[])
    if not isinstance(hosts, list):
        return []
    return [_normalize_host_record(dict(item)) for item in hosts if isinstance(item, Mapping)]


def _save_host_items(items: list[Mapping[str, Any] | AIHost]) -> None:
    config = load_app_config()
    config.setdefault("ai_host_management", {})
    config["ai_host_management"]["hosts"] = [
        _serialize_host_record(item if isinstance(item, Mapping) else item) for item in items
    ]
    save_app_config(config)


def _update_text(updates: Mapping[str, Any], key: str, current: str) -> str:
    if key not in updates:
        return current
    value = updates.get(key)
    return current if value is None else _normalize_text(value)


def _update_int(updates: Mapping[str, Any], key: str, current: int) -> int:
    if key not in updates:
        return current
    value = updates.get(key)
    parsed = _parse_int(value, default=current)
    return current if parsed is None else int(parsed)


def _update_bool(updates: Mapping[str, Any], key: str, current: bool) -> bool:
    if key not in updates:
        return current
    return _parse_bool(updates.get(key), default=current)


def _update_host_payload(existing: AIHost, updates: Mapping[str, Any]) -> AIHost:
    return replace(
        existing,
        name=_update_text(updates, "name", existing.name),
        hostname=_update_text(updates, "hostname", existing.hostname),
        role=_update_text(updates, "role", existing.role),
        connection_type=_update_text(updates, "connection_type", existing.connection_type).lower(),
        username=_update_text(updates, "username", existing.username),
        port=_update_int(updates, "port", existing.port),
        credential_ref=_update_text(updates, "credential_ref", existing.credential_ref),
        enabled=_update_bool(updates, "enabled", existing.enabled),
        notes=_update_text(updates, "notes", existing.notes),
        created_at=existing.created_at,
        updated_at=utc_now(),
    )


def validate_host_configuration(**payload: Any) -> dict[str, Any]:
    _reject_sensitive_fields(payload)
    host = AIHost(
        id=_parse_int(payload.get("id")),
        name=_normalize_text(payload.get("name")),
        hostname=_normalize_text(payload.get("hostname")),
        role=_normalize_text(payload.get("role")),
        connection_type=_normalize_text(payload.get("connection_type") or "local") or "local",
        username=_normalize_text(payload.get("username")),
        port=_parse_int(payload.get("port"), default=22) or 22,
        credential_ref=_normalize_text(payload.get("credential_ref")),
        enabled=_parse_bool(payload.get("enabled"), default=True),
        notes=_normalize_text(payload.get("notes")),
        created_at=_parse_datetime(payload.get("created_at")) if payload.get("created_at") else utc_now(),
        updated_at=_parse_datetime(payload.get("updated_at")) if payload.get("updated_at") else utc_now(),
    )
    return {"passed": True, "host": _serialize_host_record(host), "errors": []}


def inspect_local_resources() -> HostResourceSnapshot:
    meminfo = _read_meminfo()
    detected_gpus = _detect_gpus()
    vram_total_bytes, vram_free_bytes = _aggregate_gpu_vram(detected_gpus)
    return HostResourceSnapshot(
        total_ram_bytes=meminfo.get("MemTotal", 0),
        available_ram_bytes=meminfo.get("MemAvailable", 0),
        swap_total_bytes=meminfo.get("SwapTotal", 0),
        swap_free_bytes=meminfo.get("SwapFree", 0),
        vram_total_bytes=vram_total_bytes,
        vram_free_bytes=vram_free_bytes,
        detected_gpus=detected_gpus,
        collection_timestamp=utc_now(),
    )


def inspect_ai_host_resources(bootstrap_password: str | None = None) -> list[AIHostResourceReport]:
    reports: list[AIHostResourceReport] = []
    for host in AIHostManagementService().list_hosts():
        reports.append(_inspect_host_resources(host, bootstrap_password=bootstrap_password))
    return reports


def delete_ai_host(host_id: int) -> bool:
    return AIHostManagementService().delete_host(host_id)


def _read_meminfo() -> dict[str, int]:
    meminfo_path = Path("/proc/meminfo")
    if not meminfo_path.is_file():
        return {}

    values: dict[str, int] = {}
    for line in meminfo_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, remainder = line.split(":", 1)
        match = re.search(r"(\d+)\s*kB", remainder)
        if match:
            values[key.strip()] = int(match.group(1)) * 1024
    return values


def _detect_gpus() -> list[dict[str, Any]]:
    detected = _detect_nvidia_gpus()
    if detected:
        return detected
    return _detect_sysfs_gpus()


def _detect_nvidia_gpus() -> list[dict[str, Any]]:
    command = ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except (FileNotFoundError, OSError):
        return []
    if completed.returncode != 0:
        return []

    gpus: list[dict[str, Any]] = []
    for index, raw_line in enumerate(completed.stdout.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(",")]
        name = parts[0] if parts else f"GPU {index}"
        total = _megabytes_to_bytes(parts[1] if len(parts) > 1 else None)
        free = _megabytes_to_bytes(parts[2] if len(parts) > 2 else None)
        gpus.append(
            {
                "index": index,
                "name": name,
                "vendor": "nvidia",
                "source": "nvidia-smi",
                "vram_total_bytes": total,
                "vram_free_bytes": free,
            }
        )
    return gpus


def _detect_sysfs_gpus() -> list[dict[str, Any]]:
    drm_root = Path("/sys/class/drm")
    if not drm_root.exists():
        return []

    gpus: list[dict[str, Any]] = []
    for index, card_dir in enumerate(sorted(drm_root.glob("card[0-9]*"))):
        device_dir = card_dir / "device"
        if not device_dir.exists():
            continue
        vendor = _read_text(device_dir / "vendor")
        device = _read_text(device_dir / "device")
        driver = _read_sysfs_driver_name(device_dir)
        memory = _read_sysfs_gpu_memory(device_dir)
        total = memory.get("vram_total_bytes")
        free = memory.get("vram_free_bytes")
        gpu_name = _gpu_name_from_sysfs(card_dir.name, vendor=vendor, device=device, driver=driver)
        gpus.append(
            {
                "index": index,
                "name": gpu_name,
                "vendor_id": vendor,
                "device_id": device,
                "driver": driver,
                "source": "sysfs",
                "vram_total_bytes": total,
                "vram_free_bytes": free,
            }
        )
    return gpus


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""


def _read_sysfs_driver_name(device_dir: Path) -> str:
    uevent_path = device_dir / "uevent"
    try:
        contents = uevent_path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError):
        contents = []
    for line in contents:
        if line.startswith("DRIVER="):
            return line.split("=", 1)[1].strip()
    driver_link = device_dir / "driver"
    try:
        resolved = driver_link.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError):
        return ""
    return resolved.name if resolved.name != "driver" else ""


def _read_sysfs_gpu_memory(device_dir: Path) -> dict[str, int | None]:
    raw_values = {
        "vram_total_bytes": _read_sysfs_int(device_dir / "mem_info_vram_total"),
        "vram_used_bytes": _read_sysfs_int(device_dir / "mem_info_vram_used"),
        "vis_vram_total_bytes": _read_sysfs_int(device_dir / "mem_info_vis_vram_total"),
        "vis_vram_used_bytes": _read_sysfs_int(device_dir / "mem_info_vis_vram_used"),
    }

    total_candidates = [
        raw_values["vram_total_bytes"],
        raw_values["vis_vram_total_bytes"],
    ]
    used_candidates = [
        raw_values["vram_used_bytes"],
        raw_values["vis_vram_used_bytes"],
    ]
    total = _first_positive_int(total_candidates)
    used = _first_positive_int(used_candidates)
    free = None if total is None else max(total - (used or 0), 0)
    if total is None and used is not None:
        total = used
        free = used
    return {"vram_total_bytes": total, "vram_free_bytes": free}


def _read_sysfs_int(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _first_positive_int(values: list[int | None]) -> int | None:
    for value in values:
        if isinstance(value, int) and value > 0:
            return value
    return None


def _megabytes_to_bytes(value: Any) -> int | None:
    try:
        megabytes = int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return None
    return megabytes * 1024 * 1024


def _gpu_name_from_sysfs(card_name: str, *, vendor: str, device: str, driver: str) -> str:
    vendor_name = _vendor_name_from_id(vendor)
    driver_name = driver or "gpu"
    label_bits = [bit for bit in (vendor_name, driver_name, card_name, device) if bit]
    return " ".join(label_bits[:3]) if label_bits else card_name


def _vendor_name_from_id(vendor_id: str) -> str:
    normalized = vendor_id.lower().strip()
    return {
        "0x10de": "nvidia",
        "0x1002": "amd",
        "0x8086": "intel",
    }.get(normalized, normalized or "gpu")


def _aggregate_gpu_vram(detected_gpus: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    totals = [gpu.get("vram_total_bytes") for gpu in detected_gpus if isinstance(gpu.get("vram_total_bytes"), int)]
    frees = [gpu.get("vram_free_bytes") for gpu in detected_gpus if isinstance(gpu.get("vram_free_bytes"), int)]
    return (sum(totals) if totals else None, sum(frees) if frees else None)


def _gpu_summary(detected_gpus: list[dict[str, Any]]) -> str:
    if not detected_gpus:
        return "No GPUs detected"

    names: list[str] = []
    for gpu in detected_gpus[:3]:
        if not isinstance(gpu, Mapping):
            continue
        name = str(gpu.get("name") or "").strip()
        if name:
            names.append(name)

    if not names:
        return f"{len(detected_gpus)} GPU(s) detected"

    suffix = "..." if len(detected_gpus) > 3 else ""
    return f"{len(detected_gpus)} GPU(s): {', '.join(names)}{suffix}"


def _inspect_host_resources(host: AIHost, *, bootstrap_password: str | None = None) -> AIHostResourceReport:
    if host.connection_type == "local":
        snapshot = inspect_local_resources()
        return _resource_report_from_snapshot(host, snapshot, resource_status="ok")

    if host.connection_type == "ssh":
        snapshot, error = _inspect_ssh_host_resources(host, bootstrap_password=bootstrap_password)
        if snapshot is not None:
            return _resource_report_from_snapshot(host, snapshot, resource_status="ok")
        return _resource_report_error(host, error or "Unable to inspect SSH host resources.")

    return _resource_report_error(host, f"Unsupported connection type: {host.connection_type}")


def _resource_report_from_snapshot(
    host: AIHost,
    snapshot: HostResourceSnapshot,
    *,
    resource_status: str,
) -> AIHostResourceReport:
    gpus = list(snapshot.detected_gpus)
    return AIHostResourceReport(
        host_id=host.id,
        name=host.name,
        hostname=host.hostname,
        role=host.role,
        connection_type=host.connection_type,
        username=host.username,
        port=host.port,
        credential_ref=host.credential_ref,
        enabled=host.enabled,
        notes=host.notes,
        resource_status=resource_status,
        resource_error="",
        total_ram_bytes=snapshot.total_ram_bytes,
        available_ram_bytes=snapshot.available_ram_bytes,
        swap_total_bytes=snapshot.swap_total_bytes,
        swap_free_bytes=snapshot.swap_free_bytes,
        vram_total_bytes=snapshot.vram_total_bytes,
        vram_free_bytes=snapshot.vram_free_bytes,
        detected_gpu_count=len(gpus),
        detected_gpu_summary=_gpu_summary(gpus),
        detected_gpus=gpus,
        collection_timestamp=snapshot.collection_timestamp,
    )


def _resource_report_error(host: AIHost, error: str) -> AIHostResourceReport:
    return AIHostResourceReport(
        host_id=host.id,
        name=host.name,
        hostname=host.hostname,
        role=host.role,
        connection_type=host.connection_type,
        username=host.username,
        port=host.port,
        credential_ref=host.credential_ref,
        enabled=host.enabled,
        notes=host.notes,
        resource_status="unavailable",
        resource_error=error,
        collection_timestamp=utc_now(),
    )


def _is_ssh_key_mismatch_error(stderr: str) -> bool:
    """Check if the SSH error indicates a public key mismatch."""
    normalized = str(stderr or "").lower()
    return "permission denied" in normalized and ("publickey" in normalized or "key" in normalized)


def _try_bootstrap_ssh_key(
    host: AIHost,
    *,
    identity_path: str,
    public_key_path: str,
    password: str,
) -> tuple[bool, str]:
    """Attempt to install the SSH public key on the remote host using password authentication."""
    ssh_copy_id = _resolve_ssh_copy_id_binary_path()
    if ssh_copy_id is None:
        return False, "ssh-copy-id is unavailable in the Apmatia runtime."

    ssh_target = _ssh_target(host)
    if not ssh_target:
        return False, "SSH target (username@hostname) is missing."

    command = [
        ssh_copy_id,
        "-p",
        str(host.port),
        "-i",
        public_key_path,
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"UserKnownHostsFile={_SSH_KNOWN_HOSTS_FILE}",
        ssh_target,
    ]

    master_fd, slave_fd = pty.openpty()
    try:
        process = subprocess.Popen(
            command,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            text=False,
            close_fds=True,
        )
    except Exception as error:
        os.close(master_fd)
        os.close(slave_fd)
        return False, f"Failed to launch ssh-copy-id: {error}"

    os.close(slave_fd)
    output = bytearray()
    password_sent = False
    try:
        while True:
            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd in ready:
                try:
                    chunk = os.read(master_fd, 1024)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
                if not password_sent:
                    lowered = output.lower()
                    if b"password:" in lowered or b"passphrase" in lowered:
                        os.write(master_fd, password.encode("utf-8") + b"\n")
                        password_sent = True
            if process.poll() is not None and not ready:
                break
        try:
            while True:
                chunk = os.read(master_fd, 1024)
                if not chunk:
                    break
                output.extend(chunk)
        except OSError as error:
            if error.errno != errno.EIO:
                raise
    finally:
        os.close(master_fd)

    returncode = process.wait()
    decoded = output.decode("utf-8", errors="replace").strip()
    return returncode == 0, decoded or f"ssh-copy-id exited with code {returncode}"


def _inspect_ssh_host_resources(host: AIHost, *, bootstrap_password: str | None = None) -> tuple[HostResourceSnapshot | None, str | None]:
    ssh_target = _ssh_target(host)
    if not ssh_target:
        return None, "SSH hostname is missing."

    auth_note = _describe_ssh_auth_lookup(host.credential_ref)
    ssh_binary = _resolve_ssh_binary_path()
    if ssh_binary is None:
        return None, _format_ssh_probe_failure(
            "SSH client not available on this Apmatia host.",
            host=host,
            ssh_target=ssh_target,
            auth_note=auth_note,
            ssh_binary="ssh",
            stderr=None,
        )

    identity = _resolve_ssh_identity_path(host.credential_ref)
    command = [
        ssh_binary,
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={_SSH_KNOWN_HOSTS_FILE}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-p",
        str(host.port),
    ]
    if identity is not None:
        command.extend(["-i", identity])
    command.extend([ssh_target, _remote_resource_probe_command()])

    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except (FileNotFoundError, OSError) as error:
        return None, f"SSH inspection unavailable: {error}"

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        
        if _is_ssh_key_mismatch_error(stderr) and bootstrap_password:
            public_key_path = str(Path(identity).with_suffix(".pub")) if identity else None
            if public_key_path and Path(public_key_path).exists():
                bootstrap_succeeded, bootstrap_output = _try_bootstrap_ssh_key(
                    host,
                    identity_path=identity,
                    public_key_path=public_key_path,
                    password=bootstrap_password,
                )
                if bootstrap_succeeded:
                    completed = subprocess.run(command, capture_output=True, text=True, check=False)
                    if completed.returncode == 0:
                        meminfo, gpus = _parse_remote_probe_output(completed.stdout)
                        return _snapshot_from_probe(meminfo, gpus), None
                    stderr = completed.stderr.strip() or f"Retry failed with code {completed.returncode}"
        
        detail = stderr or f"ssh exited with code {completed.returncode}"
        return None, _format_ssh_probe_failure(
            "SSH inspection failed.",
            host=host,
            ssh_target=ssh_target,
            auth_note=auth_note,
            ssh_binary=ssh_binary,
            stderr=detail,
        )

    meminfo, gpus = _parse_remote_probe_output(completed.stdout)
    return _snapshot_from_probe(meminfo, gpus), None

def _remote_resource_probe_command() -> str:
    return (
        "set -eu; "
        "free -b; "
        "printf '%s\\n' '__APMATIA_GPU_START__'; "
        "if [ -d /sys/class/drm ]; then "
        "for card in /sys/class/drm/card[0-9]*; do "
        "[ -e \"$card/device/vendor\" ] || continue; "
        "index=\"${card##*card}\"; "
        "name=\"$(basename \"$card\")\"; "
        "vendor=\"$(cat \"$card/device/vendor\" 2>/dev/null || true)\"; "
        "device=\"$(cat \"$card/device/device\" 2>/dev/null || true)\"; "
        "driver=\"$(awk -F= '/^DRIVER=/{print $2; exit}' \"$card/device/uevent\" 2>/dev/null || true)\"; "
        "vram_total=\"$(cat \"$card/device/mem_info_vram_total\" 2>/dev/null || true)\"; "
        "vram_used=\"$(cat \"$card/device/mem_info_vram_used\" 2>/dev/null || true)\"; "
        "vis_total=\"$(cat \"$card/device/mem_info_vis_vram_total\" 2>/dev/null || true)\"; "
        "vis_used=\"$(cat \"$card/device/mem_info_vis_vram_used\" 2>/dev/null || true)\"; "
        "printf 'SYSFS|%s|%s|%s|%s|%s|%s|%s|%s|%s\\n' \"$index\" \"$name\" \"$vendor\" \"$device\" \"$driver\" \"$vram_total\" \"$vram_used\" \"$vis_total\" \"$vis_used\"; "
        "done; "
        "fi; "
        "if command -v nvidia-smi >/dev/null 2>&1; then "
        "nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits; "
        "fi"
    )


def _parse_remote_probe_output(output: str) -> tuple[dict[str, int], list[dict[str, Any]]]:
    meminfo_lines: list[str] = []
    gpu_lines: list[str] = []
    in_gpu_section = False
    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if line.strip() == _REMOTE_GPU_MARKER:
            in_gpu_section = True
            continue
        if in_gpu_section:
            gpu_lines.append(line)
        else:
            meminfo_lines.append(line)
    meminfo = _parse_meminfo_lines(meminfo_lines)
    if not meminfo:
        meminfo = _parse_free_lines(meminfo_lines)
    return meminfo, _parse_gpu_lines(gpu_lines)


def _parse_meminfo_lines(lines: list[str]) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, remainder = line.split(":", 1)
        match = re.search(r"(\d+)\s*kB", remainder)
        if match:
            values[key.strip()] = int(match.group(1)) * 1024
    return values


def _parse_free_lines(lines: list[str]) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        label = parts[0].rstrip(":")
        if label not in {"Mem", "Swap"}:
            continue
        if len(parts) < 4:
            continue
        try:
            total = int(parts[1])
            used = int(parts[2])
            free = int(parts[3])
        except ValueError:
            continue
        if label == "Mem":
            values["MemTotal"] = total
            values["MemUsed"] = used
            values["MemFree"] = free
            if len(parts) >= 7:
                try:
                    values["MemAvailable"] = int(parts[6])
                except ValueError:
                    pass
        else:
            values["SwapTotal"] = total
            values["SwapUsed"] = used
            values["SwapFree"] = free
    return values


def _parse_gpu_lines(lines: list[str]) -> list[dict[str, Any]]:
    gpus: list[dict[str, Any]] = []
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("NVIDIA|"):
            parts = [part.strip() for part in line.split("|")]
            name = parts[1] if len(parts) > 1 else f"GPU {index}"
            total = _megabytes_to_bytes(parts[2] if len(parts) > 2 else None)
            free = _megabytes_to_bytes(parts[3] if len(parts) > 3 else None)
            vendor = "nvidia"
            source = "ssh:nvidia-smi"
        elif line.startswith("SYSFS|"):
            parts = [part.strip() for part in line.split("|")]
            name = parts[2] if len(parts) > 2 else f"GPU {index}"
            vendor = _vendor_name_from_id(parts[3] if len(parts) > 3 else "")
            device = parts[4] if len(parts) > 4 else ""
            driver = parts[5] if len(parts) > 5 else ""
            memory = _parse_sysfs_remote_memory(parts[6:])
            total = memory.get("vram_total_bytes")
            free = memory.get("vram_free_bytes")
            if not name:
                name = _gpu_name_from_sysfs(f"card{index}", vendor=parts[3] if len(parts) > 3 else "", device=device, driver=driver)
            source = "ssh:sysfs"
        else:
            parts = [part.strip() for part in line.split(",")]
            name = parts[0] if parts else f"GPU {index}"
            total = _megabytes_to_bytes(parts[1] if len(parts) > 1 else None)
            free = _megabytes_to_bytes(parts[2] if len(parts) > 2 else None)
            vendor = "unknown"
            source = "ssh:unknown"
        gpus.append(
            {
                "index": index,
                "name": name,
                "vendor": vendor,
                "source": source,
                "vram_total_bytes": total,
                "vram_free_bytes": free,
            }
        )
    return gpus


def _parse_sysfs_remote_memory(values: list[str]) -> dict[str, int | None]:
    parsed_values = [_parse_int(value) for value in values]
    total = _first_positive_int([parsed_values[0], parsed_values[2]])
    used = _first_positive_int([parsed_values[1], parsed_values[3]])
    free = None if total is None else max(total - (used or 0), 0)
    if total is None and used is not None:
        total = used
        free = used
    return {"vram_total_bytes": total, "vram_free_bytes": free}


def _snapshot_from_probe(meminfo: dict[str, int], detected_gpus: list[dict[str, Any]]) -> HostResourceSnapshot:
    vram_total_bytes, vram_free_bytes = _aggregate_gpu_vram(detected_gpus)
    return HostResourceSnapshot(
        total_ram_bytes=meminfo.get("MemTotal", 0),
        available_ram_bytes=meminfo.get("MemAvailable", 0),
        swap_total_bytes=meminfo.get("SwapTotal", 0),
        swap_free_bytes=meminfo.get("SwapFree", 0),
        vram_total_bytes=vram_total_bytes,
        vram_free_bytes=vram_free_bytes,
        detected_gpus=detected_gpus,
        collection_timestamp=utc_now(),
    )


def _ssh_target(host: AIHost) -> str | None:
    hostname = str(host.hostname or "").strip()
    if not hostname:
        return None
    username = str(host.username or "").strip()
    return f"{username}@{hostname}" if username else hostname


def _resolve_ssh_identity_path(credential_ref: str) -> str | None:
    reference = str(credential_ref or "").strip()
    if not reference:
        return None

    if reference.lower().startswith("env:"):
        env_name = reference.split(":", 1)[1].strip()
        if not env_name:
            return None
        env_value = os.environ.get(env_name, "").strip()
        if not env_value:
            return None
        candidate = Path(env_value).expanduser()
        return str(candidate) if candidate.exists() else None

    if reference.lower().startswith(("ssh-agent:", "agent:", "keyring:", "secret:")):
        return None

    candidate = Path(reference).expanduser()
    if candidate.exists():
        return str(candidate)
    return None


def _resolve_ssh_key_target(credential_ref: str | None = None) -> Path:
    reference = str(credential_ref or "").strip()
    if not reference:
        return Path(os.environ.get("APMATIA_SSH_KEY_PATH") or os.environ.get("HOME") or "/home/apmatia") / ".apmatia" / "ssh" / "id_ed25519"

    lowered = reference.lower()
    if lowered.startswith(("env:", "ssh-agent:", "agent:", "keyring:", "secret:")):
        return Path(os.environ.get("APMATIA_SSH_KEY_PATH") or os.environ.get("HOME") or "/home/apmatia") / ".apmatia" / "ssh" / "id_ed25519"

    candidate = Path(reference).expanduser()
    if candidate.suffix == ".pub":
        return candidate.with_suffix("")
    return candidate


def _resolve_openssl_binary_path() -> str | None:
    for candidate in (shutil.which("openssl"), "/usr/bin/openssl", "/bin/openssl"):
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _public_key_path(private_key_path: Path) -> Path:
    return private_key_path.with_name(f"{private_key_path.name}.pub")


def _ssh_copy_command_for_host(*, username: str, hostname: str, credential_ref: str, port: int = 22) -> str:
    target = str(credential_ref or "").strip() or _DEFAULT_SSH_KEY_PATH
    public_key = f"{target}.pub"
    if not username or not hostname:
        return ""
    return (
        f"ssh-copy-id -p {int(port) if isinstance(port, int) else 22} -i {public_key} "
        "-o StrictHostKeyChecking=accept-new "
        "-o UserKnownHostsFile=/tmp/apmatia_known_hosts "
        f"{username}@{hostname}"
    )


def prepare_ssh_copy_command(
    *,
    username: str,
    hostname: str,
    port: int | None = None,
    credential_ref: str | None = None,
) -> dict[str, Any]:
    private_key_path = _resolve_ssh_key_target(credential_ref)
    effective_port = _parse_int(port, default=22) or 22
    command = _ssh_copy_command_for_host(
        username=str(username or "").strip(),
        hostname=str(hostname or "").strip(),
        credential_ref=str(private_key_path),
        port=effective_port,
    )
    if not command:
        raise ValueError("Username and hostname are required to prepare the SSH copy command.")

    return {
        "created": False,
        "credential_ref": str(private_key_path),
        "private_key_path": str(private_key_path),
        "public_key_path": str(_public_key_path(private_key_path)),
        "message": f"SSH copy command prepared for {username}@{hostname}.",
        "ssh_public_key_install_command": command,
        "ssh_connection_test_command": (
            "ssh -vvv "
            "-o BatchMode=yes "
            "-o IdentitiesOnly=yes "
            "-o StrictHostKeyChecking=accept-new "
            "-o UserKnownHostsFile=/tmp/apmatia_known_hosts "
            f"-p {effective_port} "
            f"{username}@{hostname}"
        ),
    }


def prepare_ssh_key_material(
    *,
    credential_ref: str | None = None,
    username: str | None = None,
    hostname: str | None = None,
    port: int | None = None,
    bootstrap_password: str | None = None,
) -> dict[str, Any]:
    openssl_binary = _resolve_openssl_binary_path()
    if openssl_binary is None:
        raise RuntimeError("SSH key generation is unavailable because openssl is not installed in the Apmatia runtime.")

    private_key_path = _resolve_ssh_key_target(credential_ref)
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        private_key_path.parent.chmod(0o700)
    except OSError:
        pass

    public_key_path = _public_key_path(private_key_path)
    created = False
    if not private_key_path.exists():
        try:
            completed = subprocess.run(
                [openssl_binary, "genpkey", "-algorithm", "ED25519", "-out", str(private_key_path)],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as error:
            raise RuntimeError(f"SSH key generation failed: {error}") from error
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise RuntimeError(stderr or f"openssl genpkey exited with code {completed.returncode}")

        try:
            public_der = subprocess.run(
                [openssl_binary, "pkey", "-in", str(private_key_path), "-pubout", "-outform", "DER"],
                capture_output=True,
                check=False,
            )
        except Exception as error:
            raise RuntimeError(f"SSH public key export failed: {error}") from error
        if public_der.returncode != 0:
            stderr = public_der.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(stderr or f"openssl pkey exited with code {public_der.returncode}")

        public_key_path.write_text(
            f"{_format_openssh_ed25519_public_key(public_der.stdout)} apmatia-ai-host\n",
            encoding="utf-8",
        )
        created = True

    try:
        private_key_path.chmod(0o600)
    except OSError:
        pass
    if public_key_path.exists():
        try:
            public_key_path.chmod(0o644)
        except OSError:
            pass

    username = str(username or "").strip()
    hostname = str(hostname or "").strip()
    effective_port = _parse_int(port, default=22) or 22
    install_command = _ssh_copy_command_for_host(
        username=username,
        hostname=hostname,
        credential_ref=str(private_key_path),
        port=effective_port,
    )
    bootstrap_result = {
        "bootstrap_attempted": False,
        "bootstrap_succeeded": False,
        "bootstrap_error": "",
    }
    if str(bootstrap_password or "").strip() and username and hostname:
        bootstrap_result["bootstrap_attempted"] = True
        succeeded, bootstrap_output = _bootstrap_ssh_public_key_with_password(
            username=username,
            hostname=hostname,
            port=effective_port,
            public_key_path=public_key_path,
            password=str(bootstrap_password or ""),
        )
        bootstrap_result["bootstrap_succeeded"] = succeeded
        if not succeeded:
            bootstrap_result["bootstrap_error"] = bootstrap_output
    elif str(bootstrap_password or "").strip():
        bootstrap_result["bootstrap_attempted"] = True
        bootstrap_result["bootstrap_error"] = "SSH bootstrap password was supplied, but username and hostname are required to install the public key."

    message = (
        f"SSH key prepared at {private_key_path}."
        if created
        else f"SSH key already exists at {private_key_path}."
    )
    if bootstrap_result["bootstrap_attempted"] and bootstrap_result["bootstrap_succeeded"]:
        message = f"{message} SSH public key installed on {username}@{hostname}."
    elif bootstrap_result["bootstrap_attempted"] and bootstrap_result["bootstrap_error"]:
        message = f"{message} SSH public key install attempted but did not complete."

    return {
        "created": created,
        "credential_ref": str(private_key_path),
        "private_key_path": str(private_key_path),
        "public_key_path": str(public_key_path),
        "message": message,
        "ssh_public_key_install_command": install_command,
        "ssh_connection_test_command": (
            "ssh -vvv "
            "-o BatchMode=yes "
            "-o IdentitiesOnly=yes "
            "-o StrictHostKeyChecking=accept-new "
            "-o UserKnownHostsFile=/tmp/apmatia_known_hosts "
            f"-p {effective_port} "
            f"{username}@{hostname}"
        )
        if username and hostname
        else "",
        **bootstrap_result,
    }


def _bootstrap_ssh_public_key_with_password(
    *,
    username: str,
    hostname: str,
    port: int,
    public_key_path: Path,
    password: str,
) -> tuple[bool, str]:
    ssh_copy_id = _resolve_ssh_copy_id_binary_path()
    if ssh_copy_id is None:
        return False, "ssh-copy-id is unavailable in the Apmatia runtime."

    command = [
        ssh_copy_id,
        "-p",
        str(port),
        "-i",
        str(public_key_path),
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"UserKnownHostsFile={_SSH_KNOWN_HOSTS_FILE}",
        f"{username}@{hostname}",
    ]

    master_fd, slave_fd = pty.openpty()
    try:
        process = subprocess.Popen(
            command,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            text=False,
            close_fds=True,
        )
    except Exception as error:
        os.close(master_fd)
        os.close(slave_fd)
        return False, f"Failed to launch ssh-copy-id: {error}"

    os.close(slave_fd)
    output = bytearray()
    password_sent = False
    try:
        while True:
            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd in ready:
                try:
                    chunk = os.read(master_fd, 1024)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
                if not password_sent:
                    lowered = output.lower()
                    if b"password:" in lowered or b"passphrase" in lowered:
                        os.write(master_fd, password.encode("utf-8") + b"\n")
                        password_sent = True
            if process.poll() is not None and not ready:
                break
        try:
            while True:
                chunk = os.read(master_fd, 1024)
                if not chunk:
                    break
                output.extend(chunk)
        except OSError as error:
            if error.errno != errno.EIO:
                raise
    finally:
        os.close(master_fd)

    returncode = process.wait()
    decoded = output.decode("utf-8", errors="replace").strip()
    return returncode == 0, decoded or f"ssh-copy-id exited with code {returncode}"


def _format_openssh_ed25519_public_key(public_key_der: bytes) -> str:
    blob = _extract_ed25519_public_key_bytes(public_key_der)
    encoded_blob = _ssh_string(b"ssh-ed25519") + _ssh_string(blob)
    return f"ssh-ed25519 {base64.b64encode(encoded_blob).decode('ascii')}"


def _extract_ed25519_public_key_bytes(public_key_der: bytes) -> bytes:
    cursor = 0

    def read_tlv(expected_tag: int | None = None) -> tuple[int, bytes]:
        nonlocal cursor
        if cursor >= len(public_key_der):
            raise ValueError("Unexpected end of DER data.")
        tag = public_key_der[cursor]
        cursor += 1
        length, cursor = _read_der_length(public_key_der, cursor)
        end = cursor + length
        if end > len(public_key_der):
            raise ValueError("Invalid DER length.")
        value = public_key_der[cursor:end]
        cursor = end
        if expected_tag is not None and tag != expected_tag:
            raise ValueError("Unexpected DER tag.")
        return tag, value

    _, seq = read_tlv(0x30)
    inner_cursor = 0

    def inner_read(expected_tag: int | None = None) -> tuple[int, bytes]:
        nonlocal inner_cursor
        if inner_cursor >= len(seq):
            raise ValueError("Unexpected end of DER data.")
        tag = seq[inner_cursor]
        inner_cursor += 1
        length, inner_cursor = _read_der_length(seq, inner_cursor)
        end = inner_cursor + length
        if end > len(seq):
            raise ValueError("Invalid DER length.")
        value = seq[inner_cursor:end]
        inner_cursor = end
        if expected_tag is not None and tag != expected_tag:
            raise ValueError("Unexpected DER tag.")
        return tag, value

    _, algorithm_sequence = inner_read(0x30)
    if algorithm_sequence != b"\x06\x03+ep":
        raise ValueError("Not an ed25519 public key.")
    _, bit_string = inner_read(0x03)
    if not bit_string or bit_string[0] != 0x00:
        raise ValueError("Unexpected public key bit string.")
    public_key = bit_string[1:]
    if len(public_key) != 32:
        raise ValueError("Unexpected ed25519 public key length.")
    return public_key


def _read_der_length(data: bytes, cursor: int) -> tuple[int, int]:
    if cursor >= len(data):
        raise ValueError("Unexpected end of DER data.")
    first = data[cursor]
    cursor += 1
    if first < 0x80:
        return first, cursor
    count = first & 0x7F
    if count == 0 or cursor + count > len(data):
        raise ValueError("Invalid DER length.")
    length = 0
    for index in range(count):
        length = (length << 8) | data[cursor + index]
    return length, cursor + count


def _ssh_string(data: bytes) -> bytes:
    return len(data).to_bytes(4, "big") + data


def _describe_ssh_auth_lookup(credential_ref: str) -> str:
    reference = str(credential_ref or "").strip()
    if not reference:
        return (
            "credential_ref is empty, so this host will rely on the Apmatia runtime's SSH defaults: "
            "ssh-agent, ~/.ssh/config, and default key files such as ~/.ssh/id_ed25519 or ~/.ssh/id_rsa."
        )

    lowered = reference.lower()
    if lowered.startswith("env:"):
        env_name = reference.split(":", 1)[1].strip()
        if not env_name:
            return "credential_ref uses env: but no environment variable name was provided."
        env_value = os.environ.get(env_name, "").strip()
        if not env_value:
            return (
                f"credential_ref points to environment variable {env_name!r}, but that variable is unset or empty "
                "inside the Apmatia runtime."
            )
        candidate = str(Path(env_value).expanduser())
        if Path(candidate).exists():
            return f"credential_ref resolved from environment variable {env_name!r} to {candidate}."
        return f"credential_ref resolved from environment variable {env_name!r} to {candidate}, but the file does not exist."

    if lowered.startswith(("ssh-agent:", "agent:", "keyring:", "secret:")):
        return (
            f"credential_ref {reference!r} is a reference-only token. This module does not resolve agent aliases, "
            "keyring entries, or secret store names yet."
        )

    candidate = Path(reference).expanduser()
    if candidate.exists():
        return f"credential_ref resolved to SSH key path {candidate}."
    return f"credential_ref points to SSH key path {candidate}, but that file does not exist in the Apmatia runtime."


def _format_ssh_probe_failure(
    message: str,
    *,
    host: AIHost,
    ssh_target: str,
    auth_note: str,
    ssh_binary: str,
    stderr: str | None,
) -> str:
    normalized_stderr = str(stderr or "").lower()
    next_step = ""
    if not str(host.credential_ref or "").strip():
        next_step = (
            "Next step: create a key on the machine running Apmatia with "
            "`mkdir -p ~/.ssh && chmod 700 ~/.ssh && ssh-keygen -t ed25519 -C \"apmatia-ai-host\" "
            "-f ~/.ssh/id_ed25519`, then add the public key to the remote host and set "
            "credential_ref to `~/.ssh/id_ed25519`."
        )
    elif "permission denied" in normalized_stderr or "publickey" in normalized_stderr:
        next_step = (
            "The Apmatia container reached the host, but the current private key was not accepted for this account. "
            "If you generated a new key in Apmatia, run the copy command from inside the same container, or point "
            "credential_ref at the private key file that actually matches the public key already installed on the host."
        )
    elif "host key verification failed" in normalized_stderr:
        next_step = (
            "The Apmatia container did not trust the host key yet. The probe now uses accept-new and a container-local "
            "known_hosts file, so this should only happen if the runtime cannot write /tmp or an old known_hosts entry "
            "conflicts with the current host key."
        )
    lines = [
        message,
        f"Host target: {ssh_target}",
        f"SSH binary: {ssh_binary}",
        f"Port: {host.port}",
        f"Connection type: {host.connection_type}",
        f"credential_ref: {host.credential_ref or '(empty)'}",
        f"Auth lookup: {auth_note}",
        "Password prompts are disabled for this probe; it only checks whether the current SSH credentials can complete a noninteractive login.",
        f"Host key acceptance is automatic in the Apmatia container using {_SSH_KNOWN_HOSTS_FILE}.",
    ]
    if stderr:
        lines.append(f"Remote error: {stderr}")
    if next_step:
        lines.append(next_step)
    return "\n".join(lines)


def _resolve_ssh_binary_path() -> str | None:
    for candidate in (shutil.which("ssh"), "/usr/bin/ssh", "/bin/ssh"):
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _resolve_ssh_copy_id_binary_path() -> str | None:
    for candidate in (shutil.which("ssh-copy-id"), "/usr/bin/ssh-copy-id", "/bin/ssh-copy-id"):
        if candidate and Path(candidate).exists():
            return candidate
    return None


class AIHostManagementService:
    def list_hosts(self) -> list[AIHost]:
        items = sorted(
            _load_host_items(),
            key=lambda item: (
                0 if bool(item.get("enabled", True)) else 1,
                str(item.get("name") or "").lower(),
                int(item.get("id") or 0),
            ),
        )
        return [AIHost(**item) for item in items]

    def get_host(self, host_id: int) -> AIHost | None:
        for item in _load_host_items():
            if int(item.get("id", -1)) == int(host_id):
                return AIHost(**item)
        return None

    def create_host(self, host: AIHost | None = None, **payload: Any) -> AIHost:
        data = dict(payload)
        if host is not None:
            data.update(asdict(host))
        _reject_sensitive_fields(data)
        items = _load_host_items()
        next_id = max((int(item.get("id", 0)) for item in items), default=0) + 1
        created = AIHost(
            id=next_id if data.get("id") in (None, "") else _parse_int(data.get("id"), default=next_id) or next_id,
            name=_normalize_text(data.get("name")),
            hostname=_normalize_text(data.get("hostname")),
            role=_normalize_text(data.get("role")),
            connection_type=_normalize_text(data.get("connection_type") or "local") or "local",
            username=_normalize_text(data.get("username")),
            port=_parse_int(data.get("port"), default=22) or 22,
            credential_ref=_normalize_text(data.get("credential_ref")),
            enabled=_parse_bool(data.get("enabled"), default=True),
            notes=_normalize_text(data.get("notes")),
            created_at=_parse_datetime(data.get("created_at")) if data.get("created_at") else utc_now(),
            updated_at=utc_now(),
        )
        items.append(_serialize_host_record(created))
        _save_host_items(items)
        return created

    def update_host(self, host_id: int, **updates: Any) -> AIHost:
        _reject_sensitive_fields(updates)
        items = _load_host_items()
        for index, item in enumerate(items):
            if int(item.get("id", -1)) != int(host_id):
                continue
            existing = AIHost(**item)
            merged = _update_host_payload(existing, updates)
            items[index] = _serialize_host_record(merged)
            _save_host_items(items)
            return merged
        raise ValueError(f"AI host not found: {host_id}")

    def disable_host(self, host_id: int) -> AIHost:
        return self.update_host(host_id, enabled=False)

    def validate_host_configuration(self, **payload: Any) -> dict[str, Any]:
        return validate_host_configuration(**payload)

    def prepare_ssh_key(
        self,
        *,
        credential_ref: str | None = None,
        username: str | None = None,
        hostname: str | None = None,
        port: int | None = None,
        bootstrap_password: str | None = None,
    ) -> dict[str, Any]:
        return prepare_ssh_key_material(
            credential_ref=credential_ref,
            username=username,
            hostname=hostname,
            port=port,
            bootstrap_password=bootstrap_password,
        )

    def prepare_ssh_copy_command(
        self,
        *,
        username: str,
        hostname: str,
        port: int | None = None,
        credential_ref: str | None = None,
    ) -> dict[str, Any]:
        return prepare_ssh_copy_command(username=username, hostname=hostname, port=port, credential_ref=credential_ref)

    def delete_host(self, host_id: int) -> bool:
        items = _load_host_items()
        next_items = [item for item in items if int(item.get("id", -1)) != int(host_id)]
        if len(next_items) == len(items):
            return False
        _save_host_items(next_items)
        return True
