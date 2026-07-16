from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, replace
from types import SimpleNamespace
from typing import Any

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution

from .models import AIHost
from .services import AIHostManagementService, inspect_ai_host_resources, validate_host_configuration


class ApmatiaAIHostManagementModuleViewProvider:
    def __init__(
        self,
        service: AIHostManagementService | None = None,
        service_factory: Callable[[], AIHostManagementService] | None = None,
    ) -> None:
        self._service = service
        self._service_factory = service_factory

    @property
    def service(self) -> AIHostManagementService:
        if self._service is None:
            if self._service_factory is None:
                self._service = AIHostManagementService()
            else:
                self._service = self._service_factory()
        return self._service

    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        del context
        if str(getattr(view, "view_id", "") or "") == "ai_host_management.resources.view":
            return [self._serialize_resource_report(report) for report in inspect_ai_host_resources()]
        return [self._serialize_host(item) for item in self.service.list_hosts()]

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        del context
        verb = str(command.metadata.get("verb") or "").strip().lower()
        if verb == "list":
            return {"items": self.list_items(view=self._host_view(), context=ModuleViewContext())}
        if verb == "create":
            bootstrap_password = str(payload.get("bootstrap_password") or "").strip()
            create_payload = {key: value for key, value in payload.items() if key != "bootstrap_password"}
            host = self.service.create_host(**create_payload)
            result = {"status": "created", "item": self._serialize_host(host)}
            if bootstrap_password and host.connection_type == "ssh":
                bootstrap_result = self.service.prepare_ssh_key(
                    credential_ref=host.credential_ref,
                    username=host.username,
                    hostname=host.hostname,
                    port=host.port,
                    bootstrap_password=bootstrap_password,
                )
                result.update(
                    {
                        "bootstrap_attempted": bool(bootstrap_result.get("bootstrap_attempted")),
                        "bootstrap_succeeded": bool(bootstrap_result.get("bootstrap_succeeded")),
                        "bootstrap_error": str(bootstrap_result.get("bootstrap_error") or ""),
                        "message": str(bootstrap_result.get("message") or ""),
                    }
                )
            return result
        if verb == "edit":
            host_id = _require_int(payload.get("item_id"))
            bootstrap_password = str(payload.get("bootstrap_password") or "").strip()
            updates = {key: value for key, value in payload.items() if key not in {"item_id", "bootstrap_password"}}
            host = self.service.update_host(host_id, **updates)
            if bootstrap_password and host.connection_type == "ssh":
                bootstrap_result = self.service.prepare_ssh_key(
                    credential_ref=host.credential_ref,
                    username=host.username,
                    hostname=host.hostname,
                    port=host.port,
                    bootstrap_password=bootstrap_password,
                )
                return {
                    "status": "updated",
                    "item": self._serialize_host(host),
                    "bootstrap_attempted": bool(bootstrap_result.get("bootstrap_attempted")),
                    "bootstrap_succeeded": bool(bootstrap_result.get("bootstrap_succeeded")),
                    "bootstrap_error": str(bootstrap_result.get("bootstrap_error") or ""),
                    "message": str(bootstrap_result.get("message") or ""),
                }
            return {"status": "updated", "item": self._serialize_host(host)}
        if verb == "disable":
            host_id = _require_int(payload.get("item_id"))
            host = self.service.disable_host(host_id)
            return {"status": "disabled", "item": self._serialize_host(host)}
        if verb == "delete":
            host_id = _require_int(payload.get("item_id"))
            deleted = self.service.delete_host(host_id)
            if not deleted:
                raise ValueError(f"AI host not found: {host_id}")
            return {"status": "deleted", "host_id": host_id}
        if verb == "inspect":
            resources = inspect_ai_host_resources()
            return {"status": "ok", "resources": [self._serialize_resource_report(item) for item in resources]}
        if verb == "validate":
            return validate_host_configuration(**payload)
        if verb == "prepare_ssh_key":
            result = self.service.prepare_ssh_key(
                credential_ref=str(payload.get("credential_ref") or ""),
                username=str(payload.get("username") or ""),
                hostname=str(payload.get("hostname") or ""),
                port=int(payload.get("port") or 22),
                bootstrap_password=str(payload.get("bootstrap_password") or ""),
            )
            username = str(payload.get("username") or "").strip()
            hostname = str(payload.get("hostname") or "").strip()
            port = int(payload.get("port") or 22)
            result["ssh_public_key_install_command"] = _format_ssh_copy_command(
                SimpleNamespace(
                    connection_type="ssh",
                    username=username,
                    hostname=hostname,
                    port=port,
                    credential_ref=result.get("credential_ref") or payload.get("credential_ref") or "",
                )
            )
            result["ssh_connection_test_command"] = _format_ssh_connection_test_command(
                SimpleNamespace(
                    connection_type="ssh",
                    username=username,
                    hostname=hostname,
                    port=port,
                    credential_ref=result.get("credential_ref") or payload.get("credential_ref") or "",
                )
            )
            return result
        if verb == "prepare_ssh_copy_command":
            return self.service.prepare_ssh_copy_command(
                username=str(payload.get("username") or ""),
                hostname=str(payload.get("hostname") or ""),
                port=int(payload.get("port") or 22),
                credential_ref=str(payload.get("credential_ref") or ""),
            )
        raise ValueError(f"Unsupported module command verb for now: {verb}")

    def _host_view(self) -> ViewContribution:
        from .views import VIEW_DESCRIPTORS

        return VIEW_DESCRIPTORS[0]

    @staticmethod
    def _serialize_host(host: AIHost) -> dict[str, Any]:
        data = asdict(host)
        data["created_at"] = host.created_at.isoformat()
        data["updated_at"] = host.updated_at.isoformat()
        return data

    @staticmethod
    def _serialize_resource_report(report: Any) -> dict[str, Any]:
        data = asdict(report)
        data["collection_timestamp"] = report.collection_timestamp.isoformat()
        data["host_summary"] = _format_host_summary(report)
        data["resource_summary"] = _format_resource_summary(report)
        data["gpu_summary"] = _format_gpu_summary(report)
        data["resource_error"] = _format_resource_error(report)
        data["troubleshooting_hint"] = _format_troubleshooting_hint(report)
        data["ssh_public_key_install_command"] = _format_ssh_copy_command(report)
        data["ssh_connection_test_command"] = _format_ssh_connection_test_command(report)
        data["ssh_resource_probe_command"] = _format_ssh_resource_probe_command(report)
        return data


def _format_host_summary(report: Any) -> str:
    parts = [
        f"ID {getattr(report, 'host_id', '')}",
        str(getattr(report, "name", "")).strip() or "Unnamed host",
        str(getattr(report, "hostname", "")).strip() or "(no hostname)",
    ]
    return " | ".join(part for part in parts if part)


def _format_resource_summary(report: Any) -> str:
    return "\n".join(
        [
            f"RAM: {_format_bytes(report.available_ram_bytes)} available / {_format_bytes(report.total_ram_bytes)} total",
            f"Swap: {_format_bytes(report.swap_free_bytes)} free / {_format_bytes(report.swap_total_bytes)} total",
        ]
    )


def _format_gpu_summary(report: Any) -> str:
    lines = [
        f"Status: {report.resource_status}",
        f"GPUs: {report.detected_gpu_summary or 'No GPUs detected'}",
    ]
    if getattr(report, "vram_total_bytes", None) is not None or getattr(report, "vram_free_bytes", None) is not None:
        lines.append(
            f"VRAM: {_format_optional_bytes(report.vram_free_bytes)} free / {_format_optional_bytes(report.vram_total_bytes)} total"
        )
    return "\n".join(lines)


def _format_resource_error(report: Any) -> str:
    lines = [f"Collected: {report.collection_timestamp.isoformat()}"]
    error = str(getattr(report, "resource_error", "")).strip()
    if error:
        lines.append(f"Error: {error}")
    return "\n".join(lines)


def _format_ssh_copy_command(report: Any) -> str:
    connection_type = str(getattr(report, "connection_type", "")).strip().lower()
    if connection_type != "ssh":
        return ""
    hostname = str(getattr(report, "hostname", "")).strip()
    username = str(getattr(report, "username", "")).strip()
    port = int(getattr(report, "port", 22) or 22)
    if not hostname or not username:
        return ""
    credential_ref = str(getattr(report, "credential_ref", "")).strip() or "~/.apmatia/ssh/id_ed25519"
    return "\n".join(
        [
            "ssh-copy-id \\",
            f"  -p {port} \\",
            f"  -i {credential_ref}.pub \\",
            "  -o StrictHostKeyChecking=accept-new \\",
            "  -o UserKnownHostsFile=/tmp/apmatia_known_hosts \\",
            f"  {username}@{hostname}",
        ]
    )


def _format_ssh_connection_test_command(report: Any) -> str:
    connection_type = str(getattr(report, "connection_type", "")).strip().lower()
    if connection_type != "ssh":
        return ""
    hostname = str(getattr(report, "hostname", "")).strip()
    username = str(getattr(report, "username", "")).strip()
    if not hostname or not username:
        return ""
    credential_ref = str(getattr(report, "credential_ref", "")).strip()
    key_option = f"-i {credential_ref} " if credential_ref else ""
    port = int(getattr(report, "port", 22) or 22)
    return "\n".join(
        [
            "ssh -vvv \\",
            f"  {key_option}-o BatchMode=yes \\",
            "  -o IdentitiesOnly=yes \\",
            "  -o StrictHostKeyChecking=accept-new \\",
            "  -o UserKnownHostsFile=/tmp/apmatia_known_hosts \\",
            f"  -p {port} \\",
            f"  {username}@{hostname}",
        ]
    )


def _format_ssh_resource_probe_command(report: Any) -> str:
    connection_type = str(getattr(report, "connection_type", "")).strip().lower()
    if connection_type != "ssh":
        return ""
    hostname = str(getattr(report, "hostname", "")).strip()
    username = str(getattr(report, "username", "")).strip()
    if not hostname or not username:
        return ""
    credential_ref = str(getattr(report, "credential_ref", "")).strip() or "~/.apmatia/ssh/id_ed25519"
    port = int(getattr(report, "port", 22) or 22)
    remote_command = (
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
    return "\n".join(
        [
            "ssh -i " + credential_ref + " \\",
            f"  -p {port} \\",
            "  -o BatchMode=yes \\",
            "  -o IdentitiesOnly=yes \\",
            "  -o StrictHostKeyChecking=accept-new \\",
            "  -o UserKnownHostsFile=/tmp/apmatia_known_hosts \\",
            f"  {username}@{hostname} \\",
            f"  '{remote_command}'",
        ]
    )


def _format_troubleshooting_hint(report: Any) -> str:
    error = str(getattr(report, "resource_error", "")).strip().lower()
    if not error:
        return ""
    if "no user exists for uid" in error or "no such user" in error:
        return (
            "SSH authentication is already working. The failure is happening after login when the remote resource probe runs. "
            "That means the key and account are probably fine, but the remote shell environment or the inspection command is failing. "
            "Run the exact resource probe command below to reproduce the failure outside Apmatia."
        )
    if "permission denied" in error or "publickey" in error:
        return (
            "The container reached the host, but the SSH key was not accepted for this account. "
            "If you generated a new key in Apmatia, copy the matching public key from inside the same container, or "
            "point credential_ref at the private key that already works on the host."
        )
    return "SSH reached the host, but the remote command did not complete cleanly. Try the connection test command below."


def _format_bytes(value: Any) -> str:
    if not isinstance(value, int):
        return "unknown"
    gib = value / (1024**3)
    if gib >= 1:
        return f"{gib:.1f} GiB"
    mib = value / (1024**2)
    if mib >= 1:
        return f"{mib:.1f} MiB"
    kib = value / 1024
    if kib >= 1:
        return f"{kib:.1f} KiB"
    return f"{value} B"


def _format_ssh_copy_command(report: Any) -> str:
    connection_type = str(getattr(report, "connection_type", "")).strip().lower()
    if connection_type != "ssh":
        return ""
    hostname = str(getattr(report, "hostname", "")).strip()
    username = str(getattr(report, "username", "")).strip()
    credential_ref = str(getattr(report, "credential_ref", "")).strip() or "~/.apmatia/ssh/id_ed25519"
    if not hostname or not username:
        return ""
    return f"ssh-copy-id -i {credential_ref}.pub {username}@{hostname}"


def _format_ssh_connection_test_command(report: Any) -> str:
    connection_type = str(getattr(report, "connection_type", "")).strip().lower()
    if connection_type != "ssh":
        return ""
    hostname = str(getattr(report, "hostname", "")).strip()
    username = str(getattr(report, "username", "")).strip()
    if not hostname or not username:
        return ""
    return f"ssh -vvv {username}@{hostname}"


def _format_optional_bytes(value: Any) -> str:
    return _format_bytes(value) if isinstance(value, int) else "unknown"


def _require_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("A valid item ID is required.") from error
