from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.core.modules import create_module_scaffold, plan_module_scaffold


def test_plan_module_scaffold_returns_expected_path_and_files(tmp_path: Path):
    plan = plan_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        description="Tasks, projects, and productivity helpers.",
        author="Nick Warner",
        base_dir=tmp_path,
    )

    assert plan.module_slug == "productivity"
    assert plan.module_path == tmp_path / "src/modules/productivity"
    assert plan.target_exists is False
    assert plan.passed is True
    assert plan.files == (
        tmp_path / "src/modules/productivity/__init__.py",
        tmp_path / "src/modules/productivity/manifest.toml",
        tmp_path / "src/modules/productivity/module.py",
        tmp_path / "src/modules/productivity/actions.py",
        tmp_path / "src/modules/productivity/tools.py",
        tmp_path / "src/modules/productivity/commands.py",
        tmp_path / "src/modules/productivity/views.py",
        tmp_path / "src/modules/productivity/README.md",
        tmp_path / "src/modules/productivity/tests/test_productivity_module.py",
    )


def test_plan_module_scaffold_does_not_create_files(tmp_path: Path):
    plan = plan_module_scaffold("productivity", display_name="Productivity", base_dir=tmp_path)

    assert plan.passed is True
    assert not plan.module_path.exists()


def test_plan_module_scaffold_reports_existing_target_path(tmp_path: Path):
    module_dir = tmp_path / "src/modules/productivity"
    module_dir.mkdir(parents=True)

    plan = plan_module_scaffold("productivity", display_name="Productivity", base_dir=tmp_path)

    assert plan.target_exists is True
    assert any("target module path already exists" in warning for warning in plan.warnings)


def test_plan_module_scaffold_invalid_slug_fails(tmp_path: Path):
    plan = plan_module_scaffold("BadSlug", display_name="Bad", base_dir=tmp_path)

    assert plan.passed is False
    assert plan.errors
    assert "lowercase letters" in plan.errors[0]


def test_plan_file_list_matches_create_scaffold_expected_file_list(tmp_path: Path):
    created = create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )
    plan = plan_module_scaffold("productivity", display_name="Productivity", base_dir=tmp_path)

    assert plan.files == created.created_files


def test_module_planning_does_not_require_streamlit(tmp_path: Path):
    code = f"""
import builtins
from pathlib import Path
original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from src.core.modules import plan_module_scaffold
result = plan_module_scaffold("productivity", display_name="Productivity", base_dir=Path({str(tmp_path)!r}))
assert result.passed is True
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
