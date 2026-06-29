from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.core.modules import (
    ModuleAlreadyExistsError,
    create_module_scaffold,
    get_workspace_module_inspection,
    plan_module_scaffold,
    list_workspace_module_inspections,
    resolve_module_target_dir,
    resolve_module_workspace_root,
    validate_module,
)
from src.core.registry import get_application_registry


def test_module_workspace_paths_resolve_under_workspace_root(tmp_path: Path):
    assert resolve_module_workspace_root(tmp_path) == tmp_path / "workspace" / "modules"
    assert resolve_module_target_dir("productivity", workspace=True, base_dir=tmp_path) == (
        tmp_path / "workspace" / "modules" / "productivity"
    )


def test_workspace_plan_does_not_write_files(tmp_path: Path):
    plan = plan_module_scaffold("productivity", display_name="Productivity", base_dir=tmp_path, workspace=True)

    assert plan.passed is True
    assert plan.module_path == tmp_path / "workspace" / "modules" / "productivity"
    assert not plan.module_path.exists()
    assert all(str(path).startswith(str(tmp_path / "workspace" / "modules" / "productivity")) for path in plan.files)


def test_workspace_create_writes_under_workspace_path(tmp_path: Path):
    created = create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    assert created.module_dir == tmp_path / "workspace" / "modules" / "productivity"
    assert (tmp_path / "workspace" / "modules" / "productivity" / "module.py").exists()
    assert (tmp_path / "workspace" / "modules" / "productivity" / "manifest.toml").exists()


def test_workspace_validate_passes_for_valid_scaffold(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    result = validate_module("productivity", base_dir=tmp_path, workspace=True)

    assert result.passed is True
    assert result.module_path == tmp_path / "workspace" / "modules" / "productivity"
    assert result.manifest is not None
    assert result.manifest.module_id == "productivity"


def test_workspace_inspection_lists_and_shows_metadata_without_loading_modules(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        description="Tasks, projects, and productivity helpers.",
        author="Nick Warner",
        base_dir=tmp_path,
        workspace=True,
    )

    before_ids = [item.module_id for item in get_application_registry().list_modules()]
    inspections = list_workspace_module_inspections(base_dir=tmp_path)
    inspection = get_workspace_module_inspection("productivity", base_dir=tmp_path)
    after_ids = [item.module_id for item in get_application_registry().list_modules()]

    assert inspections
    assert inspection is not None
    assert inspection.source == "workspace"
    assert inspection.manifest.module_id == "productivity"
    assert inspection.manifest.name == "Productivity"
    assert inspection.manifest.description == "Tasks, projects, and productivity helpers."
    assert inspection.manifest.author == "Nick Warner"
    assert inspection.actions == ()
    assert inspection.tools == ()
    assert inspection.commands == ()
    assert inspection.views == ()
    assert before_ids == after_ids
    assert "productivity" not in after_ids


def test_workspace_inspection_json_shape_includes_source(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )

    inspection = get_workspace_module_inspection("productivity", base_dir=tmp_path)
    assert inspection is not None

    payload = inspection.to_dict()

    assert payload["source"] == "workspace"
    assert payload["is_workspace"] is True
    assert payload["module"]["module_id"] == "productivity"
    assert payload["module"]["name"] == "Productivity"


def test_workspace_create_refuses_overwrite_without_force(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        workspace=True,
    )
    sentinel = tmp_path / "workspace" / "modules" / "productivity" / "module.py"
    sentinel.write_text("sentinel = True\n", encoding="utf-8")

    try:
        create_module_scaffold(
            module_slug="productivity",
            display_name="Productivity",
            base_dir=tmp_path,
            workspace=True,
        )
        raise AssertionError("expected overwrite protection")
    except ModuleAlreadyExistsError as exc:
        assert "Module already exists: productivity" in str(exc)
        assert sentinel.read_text(encoding="utf-8") == "sentinel = True\n"


def test_bundled_behavior_remains_unchanged(tmp_path: Path):
    created = create_module_scaffold("productivity", display_name="Productivity", base_dir=tmp_path)

    assert created.module_dir == tmp_path / "src" / "modules" / "productivity"
    assert created.module_dir.exists()
    assert not (tmp_path / "workspace" / "modules" / "productivity").exists()


def test_workspace_module_helpers_do_not_require_streamlit(tmp_path: Path):
    code = f"""
import builtins
from pathlib import Path
original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from src.core.modules import create_module_scaffold, plan_module_scaffold, validate_module
create_module_scaffold("productivity", display_name="Productivity", base_dir=Path({str(tmp_path)!r}), workspace=True)
assert plan_module_scaffold("productivity", display_name="Productivity", base_dir=Path({str(tmp_path)!r}), workspace=True).passed is True
assert validate_module("productivity", base_dir=Path({str(tmp_path)!r}), workspace=True).passed is True
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
