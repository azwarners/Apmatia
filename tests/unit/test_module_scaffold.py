from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import tomllib

from apmatia.core.modules import (
    CreatedModule,
    InvalidModuleSlugError,
    ModuleAlreadyExistsError,
    create_module_scaffold,
)


def test_create_module_scaffold_writes_expected_files(tmp_path: Path):
    created = create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        description="Tools for focused work.",
        author="Nick",
        base_dir=tmp_path,
    )

    assert isinstance(created, CreatedModule)
    assert created.module_slug == "productivity"
    expected_files = {
        tmp_path / "src/modules/productivity/__init__.py",
        tmp_path / "src/modules/productivity/manifest.toml",
        tmp_path / "src/modules/productivity/module.py",
        tmp_path / "src/modules/productivity/actions.py",
        tmp_path / "src/modules/productivity/tools.py",
        tmp_path / "src/modules/productivity/commands.py",
        tmp_path / "src/modules/productivity/views.py",
        tmp_path / "src/modules/productivity/README.md",
        tmp_path / "src/modules/productivity/tests/test_productivity_module.py",
    }

    assert set(created.created_files) == expected_files
    for path in expected_files:
        assert path.exists()


def test_generated_python_is_syntactically_valid(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        description="Tools for focused work.",
        author="Nick",
        base_dir=tmp_path,
    )

    for relative_path in [
        "src/modules/productivity/__init__.py",
        "src/modules/productivity/module.py",
        "src/modules/productivity/actions.py",
        "src/modules/productivity/tools.py",
        "src/modules/productivity/commands.py",
        "src/modules/productivity/views.py",
        "src/modules/productivity/tests/test_productivity_module.py",
    ]:
        path = tmp_path / relative_path
        result = subprocess.run([sys.executable, "-m", "py_compile", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


def test_generated_manifest_is_parseable(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        description="Tools for focused work.",
        author="Nick",
        base_dir=tmp_path,
    )

    manifest_path = tmp_path / "src/modules/productivity/manifest.toml"
    with manifest_path.open("rb") as handle:
        manifest = tomllib.load(handle)

    assert manifest["module"]["module_id"] == "productivity"
    assert manifest["module"]["name"] == "Productivity"
    assert manifest["module"]["author"] == "Nick"
    assert manifest["module"]["status"] == "development"
    assert manifest["module"]["category"] == "feature"
    assert manifest["module"]["default_enabled"] is True
    assert manifest["module"]["tags"] == []
    assert manifest["metadata"] == {}
    assert manifest["dependencies"] == {
        "python": "",
        "python_packages": [],
        "system_packages": [],
        "modules": [],
        "tools": [],
    }


def test_invalid_module_slugs_are_rejected(tmp_path: Path):
    invalid_slugs = [
        "",
        " ",
        "1bad",
        "bad slug",
        "bad/slug",
        "bad\\slug",
        "../bad",
        "bad..slug",
        "BadSlug",
    ]

    for slug in invalid_slugs:
        try:
            create_module_scaffold(slug, "Bad", base_dir=tmp_path)
        except InvalidModuleSlugError:
            pass
        else:
            raise AssertionError(f"Expected slug to be rejected: {slug!r}")


def test_existing_module_is_not_overwritten_without_force(tmp_path: Path):
    module_dir = tmp_path / "src/modules/productivity"
    module_dir.mkdir(parents=True)
    existing_file = module_dir / "module.py"
    existing_file.write_text("sentinel = True\n", encoding="utf-8")

    try:
        create_module_scaffold(
            module_slug="productivity",
            display_name="Productivity",
            base_dir=tmp_path,
        )
    except ModuleAlreadyExistsError:
        pass
    else:
        raise AssertionError("Expected existing module to be rejected")

    assert existing_file.read_text(encoding="utf-8") == "sentinel = True\n"


def test_existing_module_can_be_overwritten_with_force(tmp_path: Path):
    module_dir = tmp_path / "src/modules/productivity"
    module_dir.mkdir(parents=True)
    existing_file = module_dir / "module.py"
    existing_file.write_text("sentinel = True\n", encoding="utf-8")

    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
        force=True,
    )

    assert "sentinel = True" not in existing_file.read_text(encoding="utf-8")


def test_module_scaffold_does_not_require_streamlit():
    code = """
import builtins
original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from apmatia.core.modules import create_module_scaffold
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
