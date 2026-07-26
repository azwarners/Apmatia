from __future__ import annotations

from unittest.mock import patch

from apmatia.interfaces.cli.main import build_parser, main


CATALOG = [
    {
        "module_id": "agents",
        "module_name": "Agents",
        "module_description": "Create and manage agents.",
        "command_id": "agents.list",
        "path": ["agents", "list"],
        "name": "List Agents",
        "description": "List all agents.",
        "fields": [],
    },
    {
        "module_id": "agents",
        "module_name": "Agents",
        "module_description": "Create and manage agents.",
        "command_id": "agents.create",
        "path": ["agents", "create"],
        "name": "Create Agent",
        "description": "Create an agent.",
        "fields": [
            {"key": "name", "label": "Name", "data_type": "string", "required": True},
            {"key": "enabled", "label": "Enabled", "data_type": "boolean"},
        ],
    },
    {
        "module_id": "ipe",
        "module_name": "IPE",
        "module_description": "Integrated productivity environment.",
        "command_id": "ipe.idea.create",
        "path": ["ipe", "idea", "create"],
        "name": "Create Idea",
        "description": "Capture an idea.",
        "fields": [{"key": "title", "label": "Title", "required": True}],
    },
]


def test_dynamic_parser_has_root_module_and_nested_help(capsys):
    parser = build_parser(CATALOG)
    parser.print_help()
    root_help = capsys.readouterr().out
    assert "agents" in root_help
    assert "ipe" in root_help

    try:
        parser.parse_args(["agents", "--help"])
    except SystemExit as error:
        assert error.code == 0
    module_help = capsys.readouterr().out
    assert "create" in module_help
    assert "list" in module_help

    try:
        parser.parse_args(["ipe", "idea", "--help"])
    except SystemExit as error:
        assert error.code == 0
    assert "create" in capsys.readouterr().out


def test_dynamic_command_builds_payload_and_executes(capsys):
    with patch("apmatia.interfaces.cli.main.api_client.list_module_commands", return_value=CATALOG), patch(
        "apmatia.interfaces.cli.dynamic.api_client.execute_module_command",
        return_value={"status": "created"},
    ) as execute:
        exit_code = main(["agents", "create", "--name", "Planner", "--enabled"])

    assert exit_code == 0
    execute.assert_called_once_with("agents.create", {"name": "Planner", "enabled": True})
    assert '"status": "created"' in capsys.readouterr().out


def test_dynamic_command_supports_json_payload_fallback():
    with patch("apmatia.interfaces.cli.main.api_client.list_module_commands", return_value=CATALOG), patch(
        "apmatia.interfaces.cli.dynamic.api_client.execute_module_command",
        return_value={"status": "ok"},
    ) as execute:
        assert main(["agents", "list", "--payload", '{"include_disabled": true}']) == 0

    execute.assert_called_once_with("agents.list", {"include_disabled": True})


def test_no_arguments_prints_root_help(capsys):
    with patch("apmatia.interfaces.cli.main.api_client.list_module_commands", return_value=CATALOG):
        assert main([]) == 0
    output = capsys.readouterr().out
    assert "registry-driven" in output
    assert "agents" in output
