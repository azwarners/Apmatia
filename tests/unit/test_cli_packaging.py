from __future__ import annotations

import tomllib
from pathlib import Path


def test_pyproject_exposes_apmatia_console_script() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    pyproject = tomllib.loads((repository_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["apmatia"] == "apmatia.interfaces.cli.main:main"
    assert pyproject["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
