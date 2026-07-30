import io
import json
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apmatia.interfaces.cli.main import main


@pytest.fixture(autouse=True)
def _apmatia_workspace_root(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace" / "modules"))


@patch("apmatia.interfaces.cli.main.api_client.prompt")
@patch("sys.argv", ["main.py", "prompt", "Nick"])
def test_cli_with_prompt(mock_prompt_llm):
    mock_prompt_llm.return_value = "mocked cli response"
    assert main() == 0
    mock_prompt_llm.assert_called_once_with("Nick", output_dir=None)


def test_cli_module_create_success(tmp_path, capsys):
    exit_code = main(
        [
            "module",
            "create",
            "productivity",
            "--name",
            "Productivity",
            "--description",
            "Tasks, projects, and productivity helpers.",
            "--author",
            "Nick Warner",
            "--base-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"Created module scaffold at {tmp_path / 'src/modules/productivity'}" in captured.out
    assert (tmp_path / "src/modules/productivity/module.py").exists()
    assert (tmp_path / "src/modules/productivity/manifest.toml").exists()


def test_cli_module_create_invalid_slug_fails(tmp_path, capsys):
    exit_code = main(
        [
            "module",
            "create",
            "BadSlug",
            "--name",
            "Bad",
            "--base-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error:" in captured.err


def test_cli_module_create_refuses_overwrite_without_force(tmp_path, capsys):
    module_dir = tmp_path / "src/modules/productivity"
    module_dir.mkdir(parents=True)
    existing_file = module_dir / "module.py"
    existing_file.write_text("sentinel = True\n", encoding="utf-8")

    exit_code = main(
        [
            "module",
            "create",
            "productivity",
            "--name",
            "Productivity",
            "--base-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error:" in captured.err
    assert existing_file.read_text(encoding="utf-8") == "sentinel = True\n"


def test_cli_module_create_workspace_success(tmp_path, capsys):
    exit_code = main(
        [
            "module",
            "create",
            "productivity",
            "--name",
            "Productivity",
            "--base-dir",
            str(tmp_path),
            "--workspace",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"Created module scaffold at {tmp_path / 'workspace/modules/productivity'}" in captured.out
    assert (tmp_path / "workspace/modules/productivity/module.py").exists()
    assert (tmp_path / "workspace/modules/productivity/manifest.toml").exists()
    assert not (tmp_path / "src/modules/productivity").exists()


def test_cli_module_create_uses_scaffold_helper(tmp_path):
    with patch("apmatia.interfaces.cli.modules.create_module_scaffold") as mock_create_module_scaffold:
        mock_create_module_scaffold.return_value = SimpleNamespace(
            module_dir=tmp_path / "src/modules/productivity",
            created_files=(tmp_path / "src/modules/productivity/module.py",),
        )
        exit_code = main(
            [
                "module",
                "create",
                "productivity",
                "--name",
                "Productivity",
                "--base-dir",
                str(tmp_path),
            ]
        )

    assert exit_code == 0
    mock_create_module_scaffold.assert_called_once()


def test_cli_module_list_includes_worksim_module(capsys):
    exit_code = main(["module", "list"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "worksim | Worksim | 0.1.0" in captured.out
    assert "ysparr | Ysparr | 0.1.0" in captured.out


def test_cli_module_list_json_output_is_valid_json(capsys):
    exit_code = main(["module", "list", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert isinstance(payload, list)
    assert [item["module"]["module_id"] for item in payload] == [
        "agent_alarms",
        "agent_config",
        "agent_loops",
        "agent_tools",
        "agents",
        "ai_host_management",
        "ai_model_executor",
        "ai_model_manager",
        "apmatia_admin",
        "auth",
        "dev_tools",
        "discuss",
        "ipe",
        "knowledge_wiki",
        "logging",
        "memory_manager",
        "os_admin",
        "persistence",
        "preferences",
        "runtime_telemetry",
        "users",
        "worksim",
        "ysparr",
    ]
    assert payload[0]["module"]["module_id"] == "agent_alarms"
    assert payload[0]["module"]["name"] == "Agent Alarms"
    assert payload[0]["module"]["version"] == "0.1.0"
    assert payload[0]["module"]["description"] == "An experimental alarm scheduler that dispatches prompts to Agent Loops."
    assert payload[0]["module"]["author"] == "Nick"
    assert payload[0]["module"]["status"] == "development"
    assert payload[0]["module"]["category"] == "agent"
    assert payload[0]["module"]["default_enabled"] is True
    assert payload[0]["module"]["tags"] == ["alarms", "scheduler", "agent-loops", "automation"]
    assert payload[0]["module"]["metadata"] == {}
    assert payload[0]["module"]["dependencies"] == {
        "python": ">=3.10",
        "python_packages": [],
        "system_packages": [],
        "modules": ["agent_loops"],
        "tools": [],
    }
    assert payload[0]["actions"] == []
    assert payload[0]["commands"] == []
    assert payload[0]["views"] == []
    assert payload[0]["source"] == "bundled"
    assert payload[0]["is_workspace"] is False
    payload = payload[1:]
    assert payload[0]["module"]["module_id"] == "agent_config"
    assert payload[0]["module"]["name"] == "Agent Config"
    assert payload[0]["module"]["version"] == "0.1.0"
    assert payload[0]["module"]["description"] == "Configure and inspect agent workspace and knowledge directories."
    assert payload[0]["module"]["author"] == "Nick"
    assert payload[0]["module"]["status"] == "development"
    assert payload[0]["module"]["category"] == "agent"
    assert payload[0]["module"]["tags"] == ["agent-config", "knowledge", "workspace", "directories"]
    assert payload[0]["module"]["metadata"] == {}
    assert payload[0]["module"]["dependencies"] == {
        "python": ">=3.10",
        "python_packages": [],
        "system_packages": [],
        "modules": [],
        "tools": [],
    }
    assert payload[0]["actions"] == []
    assert payload[0]["commands"] == []
    assert payload[0]["views"] == []
    assert payload[0]["source"] == "bundled"
    assert payload[0]["is_workspace"] is False
    payload = payload[1:]
    assert payload[0]["module"]["module_id"] == "agent_loops"
    assert payload[0]["module"]["name"] == "Agent Loops"
    assert payload[0]["module"]["version"] == "0.1.0"
    assert payload[0]["module"]["description"] == "A long-running workspace for autonomous contact-driven task loops and run history."
    assert payload[0]["module"]["author"] == "Nick"
    assert payload[0]["module"]["status"] == "development"
    assert payload[0]["module"]["category"] == "agent"
    assert payload[0]["module"]["tags"] == ["agents", "groups", "loops", "tasks", "workspace", "runs"]
    assert payload[0]["module"]["metadata"] == {}
    assert payload[0]["module"]["dependencies"] == {
        "python": ">=3.10",
        "python_packages": [],
        "system_packages": [],
        "modules": ["persistence", "ysparr"],
        "tools": [],
    }
    assert payload[0]["actions"] == []
    assert payload[0]["commands"] == []
    assert payload[0]["views"] == []
    assert payload[0]["source"] == "bundled"
    assert payload[0]["is_workspace"] is False
    agent_tools = payload.pop(1)
    assert agent_tools["module"] == {
        "module_id": "agent_tools",
        "name": "Agent Tools",
        "version": "0.1.0",
        "description": "Define, assign, and safely execute tools used by Apmatia agents.",
        "author": "Nick",
        "status": "development",
        "category": "tool",
        "default_enabled": True,
        "tags": ["agents", "tools", "execution", "assignments"],
        "metadata": {},
        "dependencies": {
            "python": ">=3.10",
            "python_packages": [],
            "system_packages": [],
            "modules": ["persistence"],
            "tools": [],
        },
    }
    assert agent_tools["actions"] == []
    assert agent_tools["commands"] == []
    assert agent_tools["views"] == []
    assert agent_tools["source"] == "bundled"
    assert agent_tools["is_workspace"] is False
    agents = payload.pop(1)
    assert agents["module"] == {
        "module_id": "agents",
        "name": "Agents",
        "version": "0.1.0",
        "description": "Create, configure, and manage the agents that power Apmatia.",
        "author": "Nick",
        "status": "stable",
        "category": "agent",
        "default_enabled": True,
        "tags": ["agents", "prompts", "models", "workspaces", "infrastructure"],
        "metadata": {},
        "dependencies": {
            "python": ">=3.10",
            "python_packages": [],
            "system_packages": [],
            "modules": ["persistence"],
            "tools": [],
        },
    }
    assert agents["actions"] == ["agents.agents"]
    assert agents["commands"] == [
        "agents.clone",
        "agents.create",
        "agents.delete",
        "agents.edit",
        "agents.list",
    ]
    assert agents["views"] == ["agents.agents.view"]
    assert agents["source"] == "bundled"
    assert agents["is_workspace"] is False
    assert payload[1]["module"]["name"] == "AI Host Management"
    assert payload[1]["module"]["version"] == "0.1.0"
    assert payload[1]["module"]["description"] == "Track AI-capable hosts and inspect current resource utilization across registered hosts for future model placement."
    assert payload[1]["module"]["status"] == "development"
    assert payload[1]["module"]["category"] == "infrastructure"
    assert payload[1]["module"]["tags"] == ["hosts", "resources", "ssh", "local", "inventory"]
    assert payload[1]["module"]["metadata"] == {}
    assert payload[1]["module"]["dependencies"] == {
        "python": ">=3.10",
        "python_packages": [],
        "system_packages": [],
        "modules": [],
        "tools": [],
    }
    assert payload[1]["actions"] == []
    assert payload[1]["commands"] == []
    assert payload[1]["views"] == []
    assert payload[2]["module"]["name"] == "AI Model Executor"
    assert payload[2]["module"]["version"] == "0.1.0"
    assert payload[3]["module"]["name"] == "AI Model Manager"
    assert payload[3]["module"]["version"] == "0.1.0"
    assert payload[3]["module"]["description"] == "Local GGUF model metadata management with size estimates and task routing preferences."
    assert payload[3]["module"]["status"] == "stable"
    assert payload[3]["module"]["category"] == "tool"
    assert payload[3]["module"]["tags"] == ["gguf", "models", "preferences", "scanning", "estimates"]
    assert payload[3]["module"]["metadata"] == {}
    assert payload[3]["module"]["dependencies"] == {
        "python": ">=3.10",
        "python_packages": [],
        "system_packages": [],
        "modules": [],
        "tools": [],
    }
    assert payload[3]["actions"] == [
        "ai_model_manager.llm_configs",
        "ai_model_manager.models",
        "ai_model_manager.preferences",
    ]
    assert payload[3]["commands"] == [
        "ai_model_manager.llm_configs.create",
        "ai_model_manager.llm_configs.delete",
        "ai_model_manager.llm_configs.edit",
        "ai_model_manager.llm_configs.list",
        "ai_model_manager.llm_configs.test",
        "ai_model_manager.models.create",
        "ai_model_manager.models.delete",
        "ai_model_manager.models.edit",
        "ai_model_manager.models.list",
        "ai_model_manager.models.scan",
        "ai_model_manager.models.show",
        "ai_model_manager.preferences.create",
        "ai_model_manager.preferences.delete",
        "ai_model_manager.preferences.edit",
        "ai_model_manager.preferences.list",
    ]
    assert payload[3]["views"] == [
        "ai_model_manager.llm_configs.view",
        "ai_model_manager.models.view",
        "ai_model_manager.preferences.view",
    ]
    assert payload[4]["module"]["module_id"] == "apmatia_admin"
    assert payload[4]["module"]["name"] == "Apmatia Admin"
    assert payload[4]["module"]["status"] == "development"
    assert payload[4]["module"]["category"] == "core"
    assert payload[4]["module"]["metadata"] == {
        "provider_ids": [
            "builtin.apmatia_create_agent",
            "builtin.apmatia_clone_agent_as",
            "builtin.apmatia_set_agent_mode",
        ]
    }
    assert payload[4]["module"]["dependencies"] == {
        "python": ">=3.10",
        "python_packages": [],
        "system_packages": [],
        "modules": ["discuss"],
        "tools": [],
    }
    assert payload[4]["actions"] == []
    assert payload[4]["commands"] == []
    assert payload[4]["views"] == []
    payload.pop(4)
    auth = payload.pop(4)
    assert auth["module"] == {
        "module_id": "auth",
        "name": "Authentication",
        "version": "0.1.0",
        "description": "Provide authentication sessions and the Apmatia login view.",
        "author": "Nick",
        "status": "stable",
        "category": "infrastructure",
        "default_enabled": True,
        "tags": ["authentication", "sessions", "login", "access-control"],
        "metadata": {},
        "dependencies": {
            "python": ">=3.10",
            "python_packages": [],
            "system_packages": [],
            "modules": ["users"],
            "tools": [],
        },
    }
    assert auth["actions"] == ["auth.login", "auth.register"]
    assert auth["commands"] == []
    assert auth["views"] == ["auth.login.view", "auth.register.view"]
    assert auth["source"] == "bundled"
    assert auth["is_workspace"] is False
    assert payload[5]["module"]["module_id"] == "discuss"
    assert payload[5]["module"]["name"] == "Discuss"
    assert payload[5]["module"]["version"] == "0.1.0"
    assert payload[5]["module"]["description"] == "A topic-centered discussion system for organizing work, conversations, summaries, and chat targets."
    assert payload[5]["module"]["author"] == "Nick"
    assert payload[5]["module"]["status"] == "stable"
    assert payload[5]["module"]["category"] == "feature"
    assert payload[5]["module"]["tags"] == ["topics", "discussions", "summaries", "chat-targets", "turns", "migration"]
    assert payload[5]["module"]["metadata"] == {}
    assert payload[5]["module"]["dependencies"] == {
        "python": ">=3.10",
        "python_packages": [],
        "system_packages": [],
        "modules": ["persistence", "ysparr"],
        "tools": [],
    }
    assert payload[5]["actions"] == [
        "discuss.chat_targets",
        "discuss.discussions",
        "discuss.summaries",
        "discuss.topics",
        "discuss.turns",
    ]
    assert payload[5]["commands"] == [
        "discuss.chat_targets.create",
        "discuss.chat_targets.delete",
        "discuss.chat_targets.edit",
        "discuss.chat_targets.list",
        "discuss.discussion.create",
        "discuss.discussion.open",
        "discuss.discussions.create",
        "discuss.discussions.delete",
        "discuss.discussions.edit",
        "discuss.discussions.list",
        "discuss.summaries.create",
        "discuss.summaries.delete",
        "discuss.summaries.edit",
        "discuss.summaries.list",
        "discuss.topics.assess_transition",
        "discuss.topics.create",
        "discuss.topics.delete",
        "discuss.topics.edit",
        "discuss.topics.list",
        "discuss.topics.summarize",
        "discuss.turns.create",
        "discuss.turns.delete",
        "discuss.turns.edit",
        "discuss.turns.list",
    ]
    assert payload[5]["views"] == [
        "discuss.chat_targets.view",
        "discuss.discussion.view",
    ]
    assert payload[4]["module"]["module_id"] == "dev_tools"
    assert payload[4]["module"]["name"] == "Dev Tools"
    assert payload[4]["module"]["version"] == "0.1.0"
    assert payload[4]["module"]["description"] == "Developer tools for tree inspection, source reading, and dependency tracing."
    assert payload[4]["module"]["author"] == "Nick"
    assert payload[4]["module"]["status"] == "development"
    assert payload[4]["module"]["category"] == "development"
    assert payload[4]["module"]["tags"] == ["tree", "source", "imports", "inspection"]
    assert payload[4]["module"]["metadata"] == {}
    assert payload[4]["module"]["dependencies"] == {
        "python": ">=3.10",
        "python_packages": [],
        "system_packages": [],
        "modules": [],
        "tools": [],
    }
    assert payload[4]["actions"] == []
    assert payload[4]["commands"] == []
    assert payload[4]["views"] == []
    assert payload[6]["module"]["module_id"] == "ipe"
    assert payload[6]["module"]["name"] == "Integrated Productivity Environment"
    assert payload[6]["module"]["version"] == "0.1.0"
    assert payload[6]["module"]["description"] == "An integrated workspace for ideas, tasks, projects, habits, and calendar planning."
    assert payload[6]["module"]["author"] == "Nick"
    assert payload[6]["module"]["status"] == "development"
    assert payload[6]["module"]["category"] == "feature"
    assert payload[6]["module"]["tags"] == ["ideas", "tasks", "projects", "habits", "calendar", "assistant"]
    assert payload[6]["module"]["metadata"] == {}
    assert payload[6]["module"]["dependencies"]["modules"] == ["persistence"]
    assert payload[6]["actions"] == []
    assert payload[6]["commands"] == []
    assert payload[6]["views"] == []
    assert payload[7]["module"]["module_id"] == "knowledge_wiki"
    assert payload[7]["module"]["name"] == "Knowledge Wiki"
    assert payload[7]["module"]["version"] == "0.1.0"
    assert payload[7]["module"]["description"] == "Create, organize, search, and maintain hierarchical knowledge wikis."
    assert payload[7]["module"]["author"] == "Nick"
    assert payload[7]["module"]["status"] == "development"
    assert payload[7]["module"]["category"] == "feature"
    assert payload[7]["module"]["tags"] == ["knowledge", "wiki", "hierarchy", "agents"]
    assert payload[7]["module"]["metadata"] == {}
    assert payload[7]["module"]["dependencies"] == {
        "python": ">=3.10",
        "python_packages": [],
        "system_packages": [],
        "modules": ["persistence"],
        "tools": [],
    }
    assert payload[7]["actions"] == []
    assert payload[7]["commands"] == []
    assert payload[7]["views"] == []
    assert payload[8]["module"]["module_id"] == "logging"
    assert payload[8]["module"]["name"] == "Logging"
    assert payload[8]["module"]["version"] == "0.1.0"
    assert payload[8]["module"]["description"] == "Structured runtime logging and a browsable log viewer for Apmatia."
    assert payload[8]["module"]["author"] == "Nick"
    assert payload[8]["module"]["status"] == "stable"
    assert payload[8]["module"]["category"] == "core"
    assert payload[8]["module"]["tags"] == ["logging", "debugging", "observability", "diagnostics", "runtime"]
    assert payload[8]["module"]["metadata"] == {}
    assert payload[8]["module"]["dependencies"]["modules"] == ["persistence"]
    assert payload[8]["actions"] == []
    assert payload[8]["commands"] == []
    assert payload[8]["views"] == ["logging.entries.view"]
    assert payload[9]["module"]["module_id"] == "memory_manager"
    assert payload[9]["module"]["name"] == "Memory Manager"
    assert payload[9]["module"]["version"] == "0.1.0"
    assert payload[9]["module"]["description"] == "Persist, browse, edit, archive, and delete agent memories."
    assert payload[9]["module"]["author"] == "Nick"
    assert payload[9]["module"]["status"] == "development"
    assert payload[9]["module"]["category"] == "agent"
    assert payload[9]["module"]["tags"] == ["memory", "agents", "persistence", "knowledge"]
    assert payload[9]["module"]["metadata"] == {}
    assert payload[9]["module"]["dependencies"]["modules"] == ["persistence"]
    assert payload[9]["actions"] == []
    assert payload[9]["commands"] == []
    assert payload[9]["views"] == []
    assert payload[10]["module"]["module_id"] == "os_admin"
    assert payload[10]["module"]["name"] == "OS Admin"
    assert payload[10]["module"]["version"] == "0.1.0"
    assert payload[10]["module"]["description"] == "Read-only operating system administration and diagnostic tools."
    assert payload[10]["module"]["author"] == "Nick"
    assert payload[10]["module"]["status"] == "development"
    assert payload[10]["module"]["category"] == "infrastructure"
    assert payload[10]["module"]["tags"] == ["operating-system", "administration", "diagnostics", "inspection"]
    assert payload[10]["module"]["metadata"] == {}
    assert payload[10]["actions"] == []
    assert payload[10]["commands"] == []
    assert payload[10]["views"] == []
    persistence = payload.pop(11)
    assert persistence["module"] == {
        "module_id": "persistence",
        "name": "Persistence",
        "version": "0.1.0",
        "description": "Provide shared SQLite, configuration, and structured log persistence infrastructure.",
        "author": "Nick",
        "status": "stable",
        "category": "infrastructure",
        "default_enabled": True,
        "tags": ["persistence", "sqlite", "configuration", "logging", "storage"],
        "metadata": {},
        "dependencies": {
            "python": ">=3.10",
            "python_packages": [],
            "system_packages": [],
            "modules": [],
            "tools": [],
        },
    }
    assert persistence["actions"] == []
    assert persistence["commands"] == []
    assert persistence["views"] == []
    preferences = payload.pop(11)
    assert preferences["module"]["module_id"] == "preferences"
    assert preferences["module"]["name"] == "Preferences"
    assert preferences["module"]["status"] == "stable"
    assert preferences["module"]["category"] == "core"
    assert preferences["module"]["default_enabled"] is True
    assert preferences["actions"] == ["preferences.modules", "preferences.preferences"]
    assert preferences["commands"] == [
        "preferences.save",
        "preferences.set_activation",
        "preferences.set_module_order",
        "preferences.set_module_visibility",
        "preferences.set_view_order",
        "preferences.set_view_visibility",
        "preferences.update_catalog_item",
    ]
    assert preferences["views"] == ["preferences.modules.view", "preferences.preferences.view"]
    runtime_telemetry = payload.pop(11)
    assert runtime_telemetry["module"] == {
        "module_id": "runtime_telemetry",
        "name": "Runtime Telemetry",
        "version": "0.1.0",
        "description": "Parse and summarize telemetry emitted by Apmatia model runtimes.",
        "author": "Nick",
        "status": "stable",
        "category": "core",
        "default_enabled": True,
        "tags": ["telemetry", "observability", "runtime", "llama.cpp", "metrics"],
        "metadata": {},
        "dependencies": {
            "python": ">=3.10",
            "python_packages": [],
            "system_packages": [],
            "modules": [],
            "tools": [],
        },
    }
    assert runtime_telemetry["actions"] == []
    assert runtime_telemetry["commands"] == []
    assert runtime_telemetry["views"] == []
    assert payload[11]["module"]["module_id"] == "users"
    assert payload[11]["module"]["name"] == "Users"
    assert payload[11]["module"]["version"] == "0.1.0"
    assert payload[11]["module"]["description"] == "Provide user, group, and membership management."
    assert payload[11]["module"]["author"] == "Nick"
    assert payload[11]["module"]["status"] == "stable"
    assert payload[11]["module"]["category"] == "infrastructure"
    assert payload[11]["module"]["tags"] == [
        "users",
        "groups",
        "memberships",
        "access-control",
    ]
    assert payload[11]["module"]["metadata"] == {}
    assert payload[11]["module"]["dependencies"]["modules"] == ["persistence"]
    assert payload[11]["actions"] == ["users.users"]
    assert payload[11]["commands"] == [
        "users.add_member",
        "users.create",
        "users.create_group",
        "users.create_user",
        "users.delete",
        "users.delete_group",
        "users.delete_user",
        "users.edit",
        "users.edit_group",
        "users.edit_user",
        "users.list",
        "users.set_membership_enabled",
    ]
    assert payload[11]["views"] == ["users.users.view"]
    assert payload[12]["module"]["module_id"] == "worksim"
    assert payload[12]["module"]["name"] == "Worksim"
    assert payload[12]["module"]["version"] == "0.1.0"
    assert payload[12]["module"]["description"] == "A workplace simulation module centered on a persistent org chart wiki."
    assert payload[12]["module"]["author"] == "Nick"
    assert payload[12]["module"]["status"] == "development"
    assert payload[12]["module"]["category"] == "feature"
    assert payload[12]["module"]["tags"] == ["wiki", "org-chart", "agents", "teams", "simulation"]
    assert payload[12]["module"]["metadata"] == {}
    assert payload[12]["actions"] == []
    assert payload[12]["commands"] == []
    assert payload[12]["views"] == []
    assert payload[13]["module"] == {
        "module_id": "ysparr",
        "name": "Ysparr",
        "version": "0.1.0",
        "description": "Backend-agnostic generative execution and persistence infrastructure.",
        "author": "Nick",
        "status": "stable",
        "category": "infrastructure",
        "default_enabled": True,
        "tags": ["generative-ai", "execution", "streaming", "backends", "persistence"],
        "metadata": {},
        "dependencies": {
            "python": ">=3.10",
            "python_packages": ["requests", "jinja2"],
            "system_packages": [],
            "modules": [],
            "tools": [],
        },
    }
    assert payload[13]["actions"] == []
    assert payload[13]["commands"] == []
    assert payload[13]["views"] == []


def test_cli_module_show_displays_worksim_module_details(capsys):
    exit_code = main(["module", "show", "worksim"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Module: worksim" in captured.out
    assert "Name: Worksim" in captured.out
    assert "Version: 0.1.0" in captured.out
    assert "Description: A workplace simulation module centered on a persistent org chart wiki." in captured.out
    assert "Author:" in captured.out
    assert "Metadata:" in captured.out
    assert "Status: development" in captured.out
    assert "Category: feature" in captured.out
    assert "Tags: wiki, org-chart, agents, teams, simulation" in captured.out
    assert "Dependencies:" in captured.out
    assert "  Python:" in captured.out
    assert "Actions: " in captured.out
    assert "Commands: " in captured.out
    assert "Views: " in captured.out


def test_cli_module_show_json_output_is_valid_json(capsys):
    exit_code = main(["module", "show", "worksim", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["module"]["module_id"] == "worksim"
    assert payload["module"]["name"] == "Worksim"
    assert payload["module"]["version"] == "0.1.0"
    assert payload["module"]["description"] == "A workplace simulation module centered on a persistent org chart wiki."
    assert payload["module"]["author"] == "Nick"
    assert payload["source"] == "bundled"
    assert payload["is_workspace"] is False
    assert payload["module"]["status"] == "development"
    assert payload["module"]["category"] == "feature"
    assert payload["module"]["tags"] == ["wiki", "org-chart", "agents", "teams", "simulation"]
    assert payload["module"]["metadata"] == {}
    assert payload["module"]["dependencies"] == {
        "python": ">=3.10",
        "python_packages": [],
        "system_packages": [],
        "modules": [],
        "tools": [],
    }
    assert payload["actions"] == []
    assert payload["commands"] == []
    assert payload["views"] == []


def test_cli_module_show_missing_module_fails(capsys):
    exit_code = main(["module", "show", "missing"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error: module not found: missing" in captured.err


def test_cli_module_list_workspace_includes_workspace_module(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        description="Tasks, projects, and productivity helpers.",
        author="Nick Warner",
        base_dir=tmp_path,
        workspace=True,
    )

    exit_code = main(["module", "list", "--workspace", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "workspace | productivity | Productivity | 0.1.0 - Tasks, projects, and productivity helpers." in captured.out


def test_cli_module_list_workspace_json_output_is_valid_json(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    exit_code = main(["module", "list", "--workspace", "--base-dir", str(tmp_path), "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert len(payload) == 1
    assert payload[0]["module"]["module_id"] == "productivity"
    assert payload[0]["source"] == "workspace"
    assert payload[0]["is_workspace"] is True
    assert payload[0]["module"]["name"] == "Productivity"
    assert payload[0]["module"]["status"] == "development"
    assert payload[0]["module"]["category"] == "feature"
    assert payload[0]["module"]["tags"] == []
    assert payload[0]["module"]["metadata"] == {}
    assert payload[0]["module"]["dependencies"] == {
        "python": "",
        "python_packages": [],
        "system_packages": [],
        "modules": [],
        "tools": [],
    }


def test_cli_module_show_workspace_displays_workspace_module_details(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        description="Tasks, projects, and productivity helpers.",
        author="Nick Warner",
        base_dir=tmp_path,
        workspace=True,
    )
    manifest_path = tmp_path / "workspace/modules/productivity/manifest.toml"
    manifest_path.write_text(
        """
[module]
module_id = "productivity"
name = "Productivity"
version = "0.1.0"
description = "Tasks, projects, and productivity helpers."
author = "Nick Warner"

[metadata]
category = "infrastructure"
tags = ["linux", "administration", "monitoring"]

[dependencies]
python = ">=3.10"
python_packages = []
system_packages = []
modules = []
tools = []
""".lstrip(),
        encoding="utf-8",
    )

    exit_code = main(["module", "show", "productivity", "--workspace", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Source: workspace" in captured.out
    assert "Module: productivity" in captured.out
    assert "Metadata:" in captured.out
    assert "Status: development" in captured.out
    assert "Category: infrastructure" in captured.out
    assert "Tags: linux, administration, monitoring" in captured.out
    assert "Dependencies:" in captured.out
    assert "  Python: >=3.10" in captured.out
    assert "Actions:" in captured.out
    assert "Views:" in captured.out
    assert "Name: Productivity" in captured.out
    assert "Description: Tasks, projects, and productivity helpers." in captured.out
    assert "Author: Nick Warner" in captured.out


def test_cli_module_show_workspace_json_output_is_valid_json(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    exit_code = main(["module", "show", "productivity", "--workspace", "--base-dir", str(tmp_path), "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["module"]["module_id"] == "productivity"
    assert payload["source"] == "workspace"
    assert payload["is_workspace"] is True


def test_cli_module_show_workspace_missing_module_fails(tmp_path, capsys):
    exit_code = main(["module", "show", "missing", "--workspace", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error: module not found: missing" in captured.err


def test_cli_module_files_workspace_lists_files(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    (tmp_path / "workspace/modules/productivity/notes.txt").write_text("hello\n", encoding="utf-8")

    exit_code = main(["module", "files", "productivity", "--workspace", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "module.py" in captured.out
    assert "notes.txt" in captured.out


def test_cli_module_files_workspace_json_output_is_valid_json(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    (tmp_path / "workspace/modules/productivity/notes.txt").write_text("hello\n", encoding="utf-8")

    exit_code = main(["module", "files", "productivity", "--workspace", "--base-dir", str(tmp_path), "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert any(item["relative_path"] == "notes.txt" for item in payload)
    assert any(item["relative_path"] == "module.py" for item in payload)
    assert all("size_bytes" in item for item in payload)


def test_cli_module_read_workspace_file_outputs_content(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    (tmp_path / "workspace/modules/productivity/notes.txt").write_text("hello\n", encoding="utf-8")

    exit_code = main(["module", "read", "productivity", "notes.txt", "--workspace", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "hello\n"


def test_cli_module_read_workspace_missing_file_fails(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    exit_code = main(["module", "read", "productivity", "missing.txt", "--workspace", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error: Workspace file not found: missing.txt" in captured.err


def test_cli_module_write_workspace_writes_new_file_from_stdin(tmp_path, monkeypatch, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("print('hello')\n"))

    exit_code = main(
        [
            "module",
            "write",
            "productivity",
            "actions.py",
            "--workspace",
            "--stdin",
            "--base-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Wrote productivity:actions.py" in captured.out
    assert "Suggested next command: apmatia module validate productivity --workspace" in captured.out
    assert (tmp_path / "workspace/modules/productivity/actions.py").read_text(encoding="utf-8") == "print('hello')\n"


def test_cli_module_write_workspace_overwrites_existing_file_from_stdin(tmp_path, monkeypatch, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    target = tmp_path / "workspace/modules/productivity/actions.py"
    target.write_text("old = True\n", encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", io.StringIO("new = True\n"))

    exit_code = main(
        [
            "module",
            "write",
            "productivity",
            "actions.py",
            "--workspace",
            "--stdin",
            "--base-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Wrote productivity:actions.py" in captured.out
    assert target.read_text(encoding="utf-8") == "new = True\n"


def test_cli_module_write_workspace_missing_module_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("print('hello')\n"))

    exit_code = main(
        [
            "module",
            "write",
            "missing",
            "actions.py",
            "--workspace",
            "--stdin",
            "--base-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error: Workspace module not found: missing" in captured.err


def test_cli_module_write_workspace_unsafe_path_fails(tmp_path, monkeypatch, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("print('hello')\n"))

    exit_code = main(
        [
            "module",
            "write",
            "productivity",
            "../outside.py",
            "--workspace",
            "--stdin",
            "--base-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error:" in captured.err
    assert ".." in captured.err


def test_cli_module_write_requires_workspace_flag(tmp_path, monkeypatch, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("print('hello')\n"))

    exit_code = main(
        [
            "module",
            "write",
            "productivity",
            "actions.py",
            "--stdin",
            "--base-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "only supports workspace modules" in captured.err


def test_cli_module_write_requires_stdin_flag(tmp_path, monkeypatch, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("print('hello')\n"))

    exit_code = main(
        [
            "module",
            "write",
            "productivity",
            "actions.py",
            "--workspace",
            "--base-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "requires --stdin" in captured.err


def test_cli_module_read_workspace_unsafe_path_fails(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    exit_code = main(["module", "read", "productivity", "../outside.txt", "--workspace", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error:" in captured.err
    assert ".." in captured.err


def test_cli_module_files_requires_workspace_flag(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    exit_code = main(["module", "files", "productivity", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "only supports workspace modules" in captured.err


def test_cli_module_files_missing_workspace_module_fails(tmp_path, capsys):
    exit_code = main(["module", "files", "missing", "--workspace", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error: Workspace module not found: missing" in captured.err


def test_cli_module_validate_success_text_output(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )

    exit_code = main(["module", "validate", "productivity", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Module: productivity" in captured.out
    assert "Status: PASS" in captured.out


def test_cli_module_validate_json_output_is_valid_json(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )

    exit_code = main(["module", "validate", "productivity", "--base-dir", str(tmp_path), "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["module_slug"] == "productivity"
    assert payload["passed"] is True
    assert payload["manifest"]["module_id"] == "productivity"
    assert payload["registered"]["modules"] == ["productivity"]


def test_cli_module_validate_failure_returns_non_zero(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )
    (tmp_path / "src/modules/productivity/module.py").write_text("VALUE = 1\n", encoding="utf-8")

    exit_code = main(["module", "validate", "productivity", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Status: FAIL" in captured.out
    assert "register(registry) exists" in captured.out


def test_cli_module_validate_failure_json_output_is_valid_json(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )
    (tmp_path / "src/modules/productivity/module.py").write_text("VALUE = 1\n", encoding="utf-8")

    exit_code = main(["module", "validate", "productivity", "--base-dir", str(tmp_path), "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["passed"] is False
    assert payload["errors"]
    assert payload["module_slug"] == "productivity"


def test_cli_module_plan_text_output(tmp_path, capsys):
    plan = main([
        "module",
        "plan",
        "productivity",
        "--name",
        "Productivity",
        "--description",
        "Tasks, projects, and productivity helpers.",
        "--author",
        "Nick Warner",
        "--base-dir",
        str(tmp_path),
    ])

    captured = capsys.readouterr()

    assert plan == 0
    assert "Module: productivity" in captured.out
    assert "Display name: Productivity" in captured.out
    assert "Status: PASS" in captured.out
    assert "Suggested next command: apmatia module create productivity --name \"Productivity\"" in captured.out
    assert not (tmp_path / "src/modules/productivity").exists()


def test_cli_module_plan_json_output_is_valid_json(tmp_path, capsys):
    exit_code = main([
        "module",
        "plan",
        "productivity",
        "--name",
        "Productivity",
        "--base-dir",
        str(tmp_path),
        "--format",
        "json",
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["module_slug"] == "productivity"
    assert payload["module_path"].endswith("src/modules/productivity")
    assert payload["files"]
    assert payload["target_exists"] is False
    assert payload["passed"] is True
    assert payload["suggested_next_command"].startswith("apmatia module create productivity")


def test_cli_module_plan_invalid_slug_fails(capsys):
    exit_code = main(["module", "plan", "BadSlug"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error:" in captured.err
    assert "Status: FAIL" in captured.out


def test_cli_module_plan_reports_existing_target_path(tmp_path, capsys):
    (tmp_path / "src/modules/productivity").mkdir(parents=True)

    exit_code = main(["module", "plan", "productivity", "--base-dir", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Target exists: yes" in captured.out
    assert "target module path already exists" in captured.out


def test_cli_module_plan_workspace_json_output_is_valid_json(tmp_path, capsys):
    exit_code = main(
        [
            "module",
            "plan",
            "productivity",
            "--name",
            "Productivity",
            "--base-dir",
            str(tmp_path),
            "--workspace",
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["module_path"].endswith("workspace/modules/productivity")
    assert payload["files"][0].endswith("workspace/modules/productivity/__init__.py")
    assert payload["target_exists"] is False
    assert payload["passed"] is True
    assert payload["suggested_next_command"].startswith("apmatia module create productivity")
    assert "--workspace" in payload["suggested_next_command"]


def test_cli_module_invalid_format_fails():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from apmatia.interfaces.cli.main import main; raise SystemExit(main(['module', 'list', '--format', 'yaml']))",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_cli_import_does_not_require_streamlit():
    code = """
import builtins
original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
import apmatia.interfaces.cli.main
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr


def test_cli_module_validate_workspace_json_output_is_valid_json(tmp_path, capsys):
    from apmatia.core.modules import create_module_scaffold

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    exit_code = main(
        [
            "module",
            "validate",
            "productivity",
            "--base-dir",
            str(tmp_path),
            "--workspace",
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["module_path"].endswith("workspace/modules/productivity")
    assert payload["passed"] is True
    assert payload["manifest"]["module_id"] == "productivity"
