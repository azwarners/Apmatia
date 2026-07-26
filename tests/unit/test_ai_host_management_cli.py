from __future__ import annotations

from unittest.mock import patch

from apmatia.interfaces.cli.main import main


def _descriptor(command: str, *, fields=()):
    return {
        "module_id": "ai_host_management",
        "module_name": "AI Host Management",
        "module_description": "Manage AI-capable hosts.",
        "command_id": f"ai_host_management.{command}",
        "path": ["ai_host_management", *command.split(".")],
        "name": command.replace(".", " ").title(),
        "description": f"Run {command}.",
        "fields": list(fields),
    }


CATALOG = [
    _descriptor("hosts.list"),
    _descriptor(
        "hosts.create",
        fields=(
            {"key": "name", "required": True},
            {"key": "hostname", "required": True},
            {"key": "role", "required": True},
        ),
    ),
    _descriptor("hosts.delete", fields=({"key": "item_id", "data_type": "number", "required": True},)),
    _descriptor("resources.inspect_local"),
]


def test_dynamic_ai_host_commands_are_discovered_and_executed(capsys):
    with patch("apmatia.interfaces.cli.main.api_client.list_module_commands", return_value=CATALOG), patch(
        "apmatia.interfaces.cli.dynamic.api_client.execute_module_command",
        return_value={"items": [{"name": "Local node"}]},
    ) as execute:
        assert main(["ai-host-management", "hosts", "list"]) == 0

    execute.assert_called_once_with("ai_host_management.hosts.list", {})
    assert "Local node" in capsys.readouterr().out


def test_dynamic_ai_host_create_uses_generated_fields():
    with patch("apmatia.interfaces.cli.main.api_client.list_module_commands", return_value=CATALOG), patch(
        "apmatia.interfaces.cli.dynamic.api_client.execute_module_command",
        return_value={"status": "created"},
    ) as execute:
        assert main(
            [
                "ai-host-management",
                "hosts",
                "create",
                "--name",
                "SSH node",
                "--hostname",
                "10.0.0.5",
                "--role",
                "inference",
                "--payload",
                '{"connection_type":"ssh"}',
            ]
        ) == 0

    execute.assert_called_once_with(
        "ai_host_management.hosts.create",
        {"connection_type": "ssh", "name": "SSH node", "hostname": "10.0.0.5", "role": "inference"},
    )


def test_dynamic_ai_host_delete_and_resource_inspection():
    with patch("apmatia.interfaces.cli.main.api_client.list_module_commands", return_value=CATALOG), patch(
        "apmatia.interfaces.cli.dynamic.api_client.execute_module_command",
        return_value={"status": "ok"},
    ) as execute:
        assert main(["ai-host-management", "hosts", "delete", "--item-id", "7"]) == 0
        assert main(["ai-host-management", "resources", "inspect-local"]) == 0

    assert execute.call_args_list[0].args == ("ai_host_management.hosts.delete", {"item_id": 7})
    assert execute.call_args_list[1].args == ("ai_host_management.resources.inspect_local", {})
