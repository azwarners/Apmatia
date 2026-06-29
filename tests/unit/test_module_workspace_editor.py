from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.core.modules import (
    ModuleWorkspaceEditor,
    WorkspaceFileNotFoundError,
    WorkspaceModuleNotFoundError,
    WorkspacePathError,
    create_module_scaffold,
)


def test_workspace_editor_lists_files(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    editor = ModuleWorkspaceEditor(base_dir=tmp_path)
    files = editor.list_files("productivity")

    relative_paths = [item.relative_path for item in files]

    assert relative_paths == sorted(relative_paths)
    assert "manifest.toml" in relative_paths
    assert "module.py" in relative_paths
    assert "tests/test_productivity_module.py" in relative_paths


def test_workspace_editor_reads_existing_file(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    editor = ModuleWorkspaceEditor(base_dir=tmp_path)
    result = editor.read_file("productivity", "module.py")

    assert result.module_slug == "productivity"
    assert result.relative_path == "module.py"
    assert "def register(registry):" in result.content


def test_workspace_editor_writes_new_file(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    editor = ModuleWorkspaceEditor(base_dir=tmp_path)
    result = editor.write_file("productivity", "notes/todo.txt", "hello world\n")

    assert result.created is True
    assert result.relative_path == "notes/todo.txt"
    assert result.path.read_text(encoding="utf-8") == "hello world\n"


def test_workspace_editor_overwrites_existing_file(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    editor = ModuleWorkspaceEditor(base_dir=tmp_path)
    result = editor.write_file("productivity", "module.py", "VALUE = 42\n")

    assert result.created is False
    assert result.path.read_text(encoding="utf-8") == "VALUE = 42\n"


def test_workspace_editor_deletes_file(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    editor = ModuleWorkspaceEditor(base_dir=tmp_path)
    editor.write_file("productivity", "notes/todo.txt", "hello world\n")
    result = editor.delete_file("productivity", "notes/todo.txt")

    assert result.deleted is True
    assert not result.path.exists()


@pytest.mark.parametrize(
    "relative_path",
    [
        "/etc/passwd",
        "../outside.txt",
        "notes/../outside.txt",
    ],
)
def test_workspace_editor_rejects_unsafe_paths(tmp_path: Path, relative_path: str):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    editor = ModuleWorkspaceEditor(base_dir=tmp_path)

    with pytest.raises(WorkspacePathError):
        editor.write_file("productivity", relative_path, "x")

    with pytest.raises(WorkspacePathError):
        editor.read_file("productivity", relative_path)

    with pytest.raises(WorkspacePathError):
        editor.delete_file("productivity", relative_path)


def test_workspace_editor_missing_module_fails(tmp_path: Path):
    editor = ModuleWorkspaceEditor(base_dir=tmp_path)

    with pytest.raises(WorkspaceModuleNotFoundError):
        editor.list_files("missing")


def test_workspace_editor_missing_file_fails(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    editor = ModuleWorkspaceEditor(base_dir=tmp_path)

    with pytest.raises(WorkspaceFileNotFoundError):
        editor.read_file("productivity", "missing.txt")

    with pytest.raises(WorkspaceFileNotFoundError):
        editor.delete_file("productivity", "missing.txt")

    with pytest.raises(WorkspaceFileNotFoundError):
        editor.write_file("productivity", "missing.txt", "x", create=False)


def test_workspace_editor_import_does_not_require_streamlit():
    code = """
import builtins
original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from src.core.modules import ModuleWorkspaceEditor
assert ModuleWorkspaceEditor is not None
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
