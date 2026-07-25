from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import Any

from apmatia.lib.agent_management.services import AgentService
from apmatia.modules.agent_tools.registry import ToolProvider

OS_ADMIN_PROVIDER_ID = "builtin.apmatia_os_admin"
_COMMAND_TIMEOUT_SECONDS = 10
_MAX_CAPTURE_CHARS = 20_000

_ALLOWED_COMMANDS = {
    "uname",
    "hostname",
    "uptime",
    "cat",
    "df",
    "free",
    "lscpu",
    "ps",
    "top",
    "pgrep",
    "ip",
    "netstat",
    "ss",
    "ping",
    "curl",
    "systemctl",
    "whoami",
    "id",
    "who",
    "last",
    "groups",
    "ls",
    "stat",
    "find",
    "head",
    "tail",
    "journalctl",
    "dmesg",
    "dpkg",
    "apt",
    "pip",
    "lsof",
    "du",
    "grep",
    "crontab",
    "iptables",
    "ufw",
    "ssl-cert-check",
    "openssl",
    "tcpdump",
    "nmap",
    "fail2ban-client",
    "logrotate",
    "auditctl",
    "selinuxenabled",
    "getenforce",
    "nstat",
    "ethtool",
    "lspci",
    "lsblk",
    "blkid",
}


def os_admin_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "apmatia_os_admin",
            "description": (
                "Run a curated read-only operating system administration command from the approved allowlist. "
                "Use this for host inspection, process review, logs, disk usage, and other diagnostic tasks."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "enum": sorted(_ALLOWED_COMMANDS)},
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "returncode": {"type": "integer"},
                    "stdout": {"type": "string"},
                    "stderr": {"type": "string"},
                    "truncated_stdout": {"type": "boolean"},
                    "truncated_stderr": {"type": "boolean"},
                },
                "required": [
                    "command",
                    "args",
                    "returncode",
                    "stdout",
                    "stderr",
                    "truncated_stdout",
                    "truncated_stderr",
                ],
                "additionalProperties": False,
            },
            "provider_id": OS_ADMIN_PROVIDER_ID,
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {
                "builtin": True,
                "module": "os_admin",
                "allowlist": sorted(_ALLOWED_COMMANDS),
            },
        },
    ]


def build_os_admin_tool_providers(agent_service: AgentService) -> list[ToolProvider]:
    return [OsAdminToolProvider(provider_id=OS_ADMIN_PROVIDER_ID, agent_service=agent_service)]


@dataclass(slots=True)
class OsAdminToolProvider:
    provider_id: str
    agent_service: AgentService

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        if tool_call is None:
            raise ValueError("Tool call context is required.")
        command = str(arguments.get("command", "")).strip()
        if not command:
            raise ValueError("command is required.")
        if command not in _ALLOWED_COMMANDS:
            raise ValueError(f"Command is not allowed: {command}")

        raw_args = arguments.get("args", [])
        if not isinstance(raw_args, list):
            raise ValueError("args must be an array of strings.")
        args = [_coerce_string(item) for item in raw_args]

        executable = shutil.which(command)
        if executable is None:
            raise ValueError(f"Command not found on this host: {command}")

        completed = subprocess.run(
            [executable, *args],
            capture_output=True,
            text=True,
            timeout=_COMMAND_TIMEOUT_SECONDS,
            check=False,
        )

        stdout, stdout_truncated = _truncate_output(completed.stdout or "")
        stderr, stderr_truncated = _truncate_output(completed.stderr or "")
        return {
            "command": command,
            "args": args,
            "returncode": int(completed.returncode),
            "stdout": stdout,
            "stderr": stderr,
            "truncated_stdout": stdout_truncated,
            "truncated_stderr": stderr_truncated,
        }


def _coerce_string(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("args must contain only strings.")
    return value


def _truncate_output(value: str) -> tuple[str, bool]:
    if len(value) <= _MAX_CAPTURE_CHARS:
        return value, False
    return value[:_MAX_CAPTURE_CHARS] + "\n[output truncated]", True
