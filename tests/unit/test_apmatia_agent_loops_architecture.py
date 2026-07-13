from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN_IMPORTS = {
    "apmatia.lib.discussions",
    "apmatia.modules.apmatia_agent_loops.legacy",
}


def test_agent_loop_module_does_not_import_legacy_or_discussions():
    module_root = Path("/home/nick/ServerData/repos/apmatia/src/apmatia/modules/apmatia_agent_loops")
    for path in module_root.rglob("*.py"):
        if "legacy" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(alias.name == item or alias.name.startswith(f"{item}.") for item in FORBIDDEN_IMPORTS), (
                        f"{path} imports {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not any(module == item or module.startswith(f"{item}.") for item in FORBIDDEN_IMPORTS), (
                    f"{path} imports {module}"
                )
