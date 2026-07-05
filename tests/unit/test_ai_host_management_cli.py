from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from apmatia.interfaces.cli.main import main


def test_cli_ai_host_list_and_show(capsys):
    client = SimpleNamespace(
        list_ai_hosts=lambda: [
            {
                "id": 1,
                "name": "Local node",
                "hostname": "localhost",
                "role": "inference",
                "connection_type": "local",
                "enabled": True,
            }
        ],
        show_ai_host=lambda host_id: {
            "id": host_id,
            "name": "Local node",
            "hostname": "localhost",
            "role": "inference",
            "connection_type": "local",
            "username": "",
            "port": 22,
            "credential_ref": "",
            "enabled": True,
            "notes": "",
        },
    )

    with patch("apmatia.interfaces.cli.ai_host_management._api_client", return_value=client):
        exit_code = main(["ai-host-management", "list"])
        show_exit_code = main(["ai-host-management", "show", "1", "--format", "text"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert show_exit_code == 0
    assert "Local node" in captured.out
    assert "Credential ref" in captured.out


def test_cli_ai_host_add_and_validate(capsys):
    client = SimpleNamespace(
        create_ai_host=lambda **payload: {"id": 7, **payload},
        validate_ai_host=lambda **payload: {"passed": True, "errors": [], "host": {"id": None, **payload}},
    )

    with patch("apmatia.interfaces.cli.ai_host_management._api_client", return_value=client):
        add_exit_code = main(
            [
                "ai-host-management",
                "add",
                "--name",
                "SSH node",
                "--hostname",
                "10.0.0.5",
                "--role",
                "inference",
                "--connection-type",
                "ssh",
                "--username",
                "nick",
                "--credential-ref",
                "~/.ssh/id_ed25519",
                "--format",
                "text",
            ]
        )
        validate_exit_code = main(
            [
                "ai-host-management",
                "test",
                "--name",
                "SSH node",
                "--hostname",
                "10.0.0.5",
                "--role",
                "inference",
                "--connection-type",
                "ssh",
                "--username",
                "nick",
                "--credential-ref",
                "~/.ssh/id_ed25519",
                "--format",
                "text",
            ]
        )

    captured = capsys.readouterr()

    assert add_exit_code == 0
    assert validate_exit_code == 0
    assert "Created AI host 7" in captured.out
    assert "Validation passed." in captured.out


def test_cli_ai_host_delete(capsys):
    client = SimpleNamespace(delete_ai_host=lambda host_id: {"status": "deleted", "host_id": host_id})

    with patch("apmatia.interfaces.cli.ai_host_management._api_client", return_value=client):
        exit_code = main(["ai-host-management", "delete", "7", "--format", "text"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Deleted AI host 7" in captured.out


def test_cli_ai_host_inspect_summaries(capsys):
    client = SimpleNamespace(
        inspect_ai_host_resources=lambda bootstrap_password=None: [
            {
                "host_id": 1,
                "name": "AI PC",
                "hostname": "192.168.86.132",
                "resource_status": "ok",
                "available_ram_bytes": 8,
                "total_ram_bytes": 16,
                "vram_free_bytes": 6,
                "vram_total_bytes": 8,
                "detected_gpu_count": 1,
            }
        ]
    )

    with patch("apmatia.interfaces.cli.ai_host_management._api_client", return_value=client):
        exit_code = main(["ai-host-management", "inspect", "--format", "text"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "AI PC" in captured.out
    assert "resource_status" not in captured.out

