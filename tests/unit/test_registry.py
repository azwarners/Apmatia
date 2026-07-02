from __future__ import annotations

import subprocess
import sys

from apmatia.core.registry import ActionContribution, CommandContribution, ModuleMetadata, Registry, ViewContribution
from apmatia.modules.apmatia_worksim.module import register as register_worksim_module


def test_registry_registers_and_lists_module():
    registry = Registry()
    module = ModuleMetadata(module_id="example", name="Example Module", version="0.1.0")

    registry.register_module(module)

    assert registry.list_modules() == [module]


def test_registry_registers_and_lists_action():
    registry = Registry()
    action = ActionContribution(
        module_id="example",
        action_id="example.action",
        name="Example Action",
    )

    registry.register_action(action)

    assert registry.list_actions() == [action]


def test_registry_registers_and_lists_command():
    registry = Registry()
    command = CommandContribution(
        module_id="example",
        action_id="example.action",
        command_id="example.command",
        name="Example Command",
    )

    registry.register_command(command)

    assert registry.list_commands() == [command]


def test_registry_registers_and_lists_view():
    registry = Registry()
    view = ViewContribution(
        module_id="example",
        action_id="example.action",
        view_id="example.view",
        name="Example View",
    )

    registry.register_view(view)

    assert registry.list_views() == [view]


def test_worksim_module_registers_into_registry():
    registry = Registry()

    register_worksim_module(registry)

    assert registry.list_modules() == [
        ModuleMetadata(
            module_id="apmatia_worksim",
            name="Apmatia Worksim",
            version="0.1.0",
            description="A workplace simulation module centered on a persistent org chart wiki.",
            metadata={
                "category": "workspace",
                "tags": ["wiki", "org-chart", "agents", "teams", "simulation"],
            },
        )
    ]
    assert [action.action_id for action in registry.list_actions()] == ["apmatia_worksim.org_chart_node"]
    assert [command.command_id for command in registry.list_commands()] == [
        "apmatia_worksim.org_chart_node.create",
        "apmatia_worksim.org_chart_node.delete",
        "apmatia_worksim.org_chart_node.edit",
        "apmatia_worksim.org_chart_node.list",
    ]
    assert [view.view_id for view in registry.list_views()] == ["apmatia_worksim.org_chart_node.view"]


def test_core_registry_import_does_not_require_streamlit():
    code = """
import builtins
original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
import importlib
importlib.import_module("apmatia.core.registry")
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
