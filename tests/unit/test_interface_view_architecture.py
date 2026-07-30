from __future__ import annotations

import ast
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INTERFACES_ROOT = REPO_ROOT / "src" / "apmatia" / "interfaces"
STREAMLIT_ROOT = INTERFACES_ROOT / "streamlit"
MODULES_ROOT = REPO_ROOT / "src" / "apmatia" / "modules"


# Temporary Phase 0 debt inventory. Entries must be removed as their views migrate. Adding an
# entry requires an explicit architecture decision; an unreviewed new special case fails the test.
ALLOWED_HARDCODED_VIEW_CHECKS = set()

ALLOWED_RENDERER_TOKENS = set()

ALLOWED_RENDERER_DISPATCH = set()

ALLOWED_CUSTOM_STREAMLIT_SCREENS = set()

ALLOWED_STREAMLIT_PAGE_FILES = {"pages/__init__.py", "pages/module_views.py"}

ALLOWED_INTERFACE_LAYER_IMPORTS = {
    ("cli/modules.py", "apmatia.core.modules"),
    ("streamlit/app.py", "apmatia.modules.persistence.logger"),
    ("streamlit/module_views/adapter.py", "apmatia.core.view_contract.normalization"),
    ("streamlit/module_views/models.py", "apmatia.core.view_contract.models"),
    ("streamlit/module_views/__init__.py", "apmatia.core.view_contract.models"),
    ("streamlit/module_views/__init__.py", "apmatia.core.view_contract.normalization"),
    ("streamlit/module_views/page.py", "apmatia.core.registry"),
    ("streamlit/module_views/page.py", "apmatia.core.view_contract.models"),
    ("streamlit/module_views/page.py", "apmatia.core.view_contract.normalization"),
    ("streamlit/module_views/renderers.py", "apmatia.core.view_contract.models"),
    ("streamlit/pages/module_views.py", "apmatia.core.view_contract.normalization"),
    ("streamlit/page_runtime.py", "apmatia.modules.persistence.logger"),
}

BANNED_MODULE_GUI_IMPORTS = (
    "streamlit",
    "tkinter",
    "PyQt",
    "PySide",
    "kivy",
    "wx",
)


def test_hardcoded_streamlit_module_and_view_checks_are_frozen():
    assert _hardcoded_view_checks() == ALLOWED_HARDCODED_VIEW_CHECKS


def test_custom_renderer_escape_hatches_are_frozen():
    assert _renderer_declarations() == ALLOWED_RENDERER_TOKENS
    assert _renderer_dispatch_tokens() == ALLOWED_RENDERER_DISPATCH


def test_custom_streamlit_module_screens_and_pages_are_frozen():
    assert _custom_streamlit_screens() == ALLOWED_CUSTOM_STREAMLIT_SCREENS
    page_files = {
        path.relative_to(STREAMLIT_ROOT).as_posix()
        for path in (STREAMLIT_ROOT / "pages").glob("*.py")
    }
    assert page_files == ALLOWED_STREAMLIT_PAGE_FILES


def test_interface_layer_dependency_exceptions_are_frozen():
    assert _interface_layer_imports() == ALLOWED_INTERFACE_LAYER_IMPORTS


def test_modules_do_not_import_gui_frameworks():
    violations: set[tuple[str, str]] = set()
    for path in MODULES_ROOT.rglob("*.py"):
        for imported in _imports(path):
            if imported.startswith(BANNED_MODULE_GUI_IMPORTS):
                violations.add((path.relative_to(MODULES_ROOT).as_posix(), imported))
    assert violations == set()


def test_public_authentication_uses_serialized_contract_renderer():
    app_source = (STREAMLIT_ROOT / "app.py").read_text(encoding="utf-8")
    auth_source = (INTERFACES_ROOT.parent / "api" / "internal" / "auth.py").read_text(encoding="utf-8")

    assert "render_view_document(view)" in app_source
    assert "render_module_view_page(view)" not in app_source
    assert "adapt_module_view" not in app_source
    assert "normalize_view_document(view).to_dict()" in auth_source


def _hardcoded_view_checks() -> set[tuple[str, str, str]]:
    module_ids = {path.name for path in MODULES_ROOT.iterdir() if path.is_dir()}
    checks: set[tuple[str, str, str]] = set()
    for path in STREAMLIT_ROOT.rglob("*.py"):
        relative = path.relative_to(STREAMLIT_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function_stack: list[str] = []

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                function_stack.append(node.name)
                self.generic_visit(node)
                function_stack.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Compare(self, node: ast.Compare) -> None:
                for candidate in (node.left, *node.comparators):
                    if not isinstance(candidate, ast.Constant) or not isinstance(candidate.value, str):
                        continue
                    literal = candidate.value
                    if literal in module_ids or literal.endswith(".view"):
                        checks.add((relative, function_stack[-1] if function_stack else "<module>", literal))
                self.generic_visit(node)

        Visitor().visit(tree)
    return checks


def _renderer_declarations() -> set[tuple[str, str]]:
    declarations: set[tuple[str, str]] = set()
    for path in MODULES_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "renderer"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    declarations.add((path.relative_to(MODULES_ROOT).as_posix(), value.value))
    return declarations


def _renderer_dispatch_tokens() -> set[tuple[str, str]]:
    dispatch: set[tuple[str, str]] = set()
    pattern = re.compile(r'get\("renderer"\).*?==\s*"([^"]+)"')
    for path in STREAMLIT_ROOT.rglob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = pattern.search(line)
            if match:
                dispatch.add((path.relative_to(STREAMLIT_ROOT).as_posix(), match.group(1)))
    return dispatch


def _custom_streamlit_screens() -> set[str]:
    screens: set[str] = set()
    for path in (STREAMLIT_ROOT / "module_views").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports_streamlit = any(imported.startswith("streamlit") for imported in _imports(path))
        has_render = any(isinstance(node, ast.FunctionDef) and node.name == "render" for node in tree.body)
        if imports_streamlit and has_render:
            screens.add(path.relative_to(STREAMLIT_ROOT).as_posix())
    return screens


def _interface_layer_imports() -> set[tuple[str, str]]:
    imports: set[tuple[str, str]] = set()
    for path in INTERFACES_ROOT.rglob("*.py"):
        for imported in _imports(path):
            if imported == "apmatia.core" or imported.startswith("apmatia.core."):
                imports.add((path.relative_to(INTERFACES_ROOT).as_posix(), imported))
            elif imported == "apmatia.modules" or imported.startswith("apmatia.modules."):
                imports.add((path.relative_to(INTERFACES_ROOT).as_posix(), imported))
    return imports


def _imports(path: Path) -> set[str]:
    imported: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    return imported
