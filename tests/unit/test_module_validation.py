from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from apmatia.core.modules import create_module_scaffold, validate_module


def test_validate_module_passes_for_valid_scaffold(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        description="Tasks, projects, and productivity helpers.",
        author="Nick Warner",
        base_dir=tmp_path,
    )

    result = validate_module("productivity", base_dir=tmp_path)

    assert result.passed is True
    assert result.module_slug == "productivity"
    assert result.module_path == tmp_path / "src/modules/productivity"
    assert result.manifest is not None
    assert result.manifest.module_id == "productivity"
    assert result.registered["modules"] == ["productivity"]


def test_validate_module_passes_with_dependency_metadata(tmp_path: Path):
    create_module_scaffold(
        module_slug="system_administration",
        display_name="System Administration",
        description="Tools for system health.",
        author="Nick Warner",
        base_dir=tmp_path,
    )
    manifest_path = tmp_path / "src/modules/system_administration/manifest.toml"
    manifest_path.write_text(
        """
[module]
module_id = "system_administration"
name = "System Administration"
version = "0.1.0"
description = "Tools for system health."
author = "Nick Warner"

[metadata]
category = "infrastructure"
tags = ["linux", "administration", "monitoring"]

[dependencies]
python = ">=3.10"
python_packages = ["psutil"]
system_packages = ["procps"]
modules = ["system_audit"]
tools = ["system_audit.inspect"]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_module("system_administration", base_dir=tmp_path)

    assert result.passed is True
    assert result.manifest is not None
    assert result.manifest.category.value == "infrastructure"
    assert result.manifest.tags == ("linux", "administration", "monitoring")
    assert result.manifest.metadata == {}
    assert result.manifest.dependencies == {
        "python": ">=3.10",
        "python_packages": ["psutil"],
        "system_packages": ["procps"],
        "modules": ["system_audit"],
        "tools": ["system_audit.inspect"],
    }


def test_validate_module_missing_required_file_fails(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )
    (tmp_path / "src/modules/productivity/actions.py").unlink()

    result = validate_module("productivity", base_dir=tmp_path)

    assert result.passed is False
    assert any(not check.passed and check.name == "required file: actions.py" for check in result.checks)
    assert any("missing required file: actions.py" in error for error in result.errors)


def test_validate_module_invalid_toml_fails(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )
    manifest_path = tmp_path / "src/modules/productivity/manifest.toml"
    manifest_path.write_text("not = [valid", encoding="utf-8")

    result = validate_module("productivity", base_dir=tmp_path)

    assert result.passed is False
    assert any(not check.passed and check.name == "manifest parses" for check in result.checks)
    assert any("failed to parse" in error for error in result.errors)


def test_validate_module_invalid_python_syntax_fails(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )
    module_path = tmp_path / "src/modules/productivity/module.py"
    module_path.write_text("def register(registry):\n    if True print('bad')\n", encoding="utf-8")

    result = validate_module("productivity", base_dir=tmp_path)

    assert result.passed is False
    assert any(not check.passed and check.name == "python syntax: module.py" for check in result.checks)


def test_validate_module_missing_register_fails(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )
    module_path = tmp_path / "src/modules/productivity/module.py"
    module_path.write_text("VALUE = 1\n", encoding="utf-8")

    result = validate_module("productivity", base_dir=tmp_path)

    assert result.passed is False
    assert any(not check.passed and check.name == "register(registry) exists" for check in result.checks)


def test_validate_module_register_raising_fails(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )
    module_path = tmp_path / "src/modules/productivity/module.py"
    module_path.write_text(
        "from __future__ import annotations\n\n"
        "from apmatia.core.registry import ModuleMetadata\n\n"
        "PRODUCTIVITY_MODULE = ModuleMetadata(module_id='productivity', name='Productivity')\n\n"
        "def register(registry):\n"
        "    raise RuntimeError('boom')\n",
        encoding="utf-8",
    )

    result = validate_module("productivity", base_dir=tmp_path)

    assert result.passed is False
    assert any(not check.passed and check.name == "register(registry) succeeds" for check in result.checks)
    assert any("raised an exception" in error for error in result.errors)


def test_validate_module_rejects_malformed_dependency_metadata(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )
    manifest_path = tmp_path / "src/modules/productivity/manifest.toml"
    manifest_path.write_text(
        """
[module]
module_id = "productivity"
name = "Productivity"
version = "0.1.0"
description = ""
author = ""

[metadata]
category = ["wrong"]
tags = ["ok", 1]

[dependencies]
python = [">=3.10"]
python_packages = ["psutil", 2]
system_packages = "procps"
modules = [1]
tools = ["system_audit.inspect", 2]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_module("productivity", base_dir=tmp_path)

    assert result.passed is False
    assert any(not check.passed and check.name == "manifest parses" for check in result.checks)
    assert any("Unsupported module category" in error for error in result.errors)


def test_module_validation_does_not_require_streamlit(tmp_path: Path):
    create_module_scaffold(
        module_slug="productivity",
        display_name="Productivity",
        base_dir=tmp_path,
    )
    code = f"""
import builtins
from pathlib import Path
original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from apmatia.core.modules import validate_module
result = validate_module("productivity", base_dir=Path({str(tmp_path)!r}))
assert result.passed is True
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
