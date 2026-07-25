from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apmatia.modules.agents.services import AgentService
from apmatia.modules.agent_tools.registry import ToolProvider

DEV_TOOLS_PROVIDER_IDS = {
    "tree": "builtin.apmatia_tree",
    "read": "builtin.apmatia_read",
    "trace_import": "builtin.apmatia_trace_import",
}

_DEFAULT_TREE_DEPTH = 3
_MAX_READ_FILE_LINES = 1000
_READ_FILE_EDGE_LINES = 50
_NOISE_NAMES = {"__pycache__", ".git", ".env", "venv", ".venv"}
_ENTRY_POINT_NAMES = {"main.py", "cli.py", "app.py", "__main__.py"}


def dev_tools_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "apmatia_tree",
            "description": "Return a JSON tree for a directory, filtering noisy folders and highlighting package entry points.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "root_dir": {"type": "string"},
                    "depth": {"type": "integer", "default": _DEFAULT_TREE_DEPTH},
                },
                "required": ["root_dir"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": DEV_TOOLS_PROVIDER_IDS["tree"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "library": "dev_tools", "tool": "tree"},
        },
        {
            "name": "apmatia_read",
            "description": "Read a source file and return its raw content with line-count and size metadata.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                },
                "required": ["file_path"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": DEV_TOOLS_PROVIDER_IDS["read"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "library": "dev_tools", "tool": "read_file"},
        },
        {
            "name": "apmatia_trace_import",
            "description": "Trace a Python module's imports, classify dependencies, and flag circular references.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "module_path": {"type": "string"},
                },
                "required": ["module_path"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": DEV_TOOLS_PROVIDER_IDS["trace_import"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "library": "dev_tools", "tool": "trace_import"},
        },
    ]


@dataclass(slots=True)
class DevToolsToolProvider:
    provider_id: str
    action: str
    agent_service: AgentService
    base_dir: Path | None = None

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        try:
            if tool_call is None:
                raise ValueError("Tool call context is required.")

            agent = self.agent_service.get_agent(int(tool_call.requester_agent_id))
            if agent is None or agent.id is None:
                raise ValueError(f"Calling agent is unavailable: {tool_call.requester_agent_id}")

            roots = _agent_scoped_roots(agent, base_dir=self.base_dir)
            if self.action == "tree":
                root_path, resolved_root = _resolve_scoped_path(str(arguments["root_dir"]), roots)
                return _inspect_tree(root_path, depth=arguments.get("depth"), repo_root=resolved_root)
            if self.action == "read":
                file_path, resolved_root = _resolve_scoped_path(str(arguments["file_path"]), roots)
                return _read_source_file(file_path, repo_root=resolved_root)
            if self.action == "trace_import":
                module_path, resolved_root = _resolve_scoped_path(str(arguments["module_path"]), roots)
                return _trace_imports(module_path, repo_root=resolved_root)
            raise ValueError(f"Unsupported dev tools action: {self.action}")
        except (FileNotFoundError, NotADirectoryError, IsADirectoryError, PermissionError, ValueError) as exc:
            return _error_result("DEV_TOOLS_ERROR", str(exc), action=self.action)
        except Exception as exc:  # pragma: no cover - defensive guard
            return _error_result("DEV_TOOLS_ERROR", str(exc), action=self.action, exception_type=type(exc).__name__)


def build_dev_tools_tool_providers(
    agent_service: AgentService,
    base_dir: Path | None = None,
) -> list[DevToolsToolProvider]:
    return [
        DevToolsToolProvider(DEV_TOOLS_PROVIDER_IDS["tree"], "tree", agent_service=agent_service, base_dir=base_dir),
        DevToolsToolProvider(DEV_TOOLS_PROVIDER_IDS["read"], "read", agent_service=agent_service, base_dir=base_dir),
        DevToolsToolProvider(
            DEV_TOOLS_PROVIDER_IDS["trace_import"],
            "trace_import",
            agent_service=agent_service,
            base_dir=base_dir,
        ),
    ]


def _inspect_tree(root_dir: Path, *, depth: Any, repo_root: Path) -> dict[str, Any]:
    root_path = root_dir.resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Directory not found: {root_dir}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root_dir}")

    max_depth = _DEFAULT_TREE_DEPTH if depth is None else _coerce_positive_int(depth, field_name="depth")
    node = _build_tree_node(root_path, current_depth=0, max_depth=max_depth)
    stats = _tree_stats(node)
    return {
        "ok": True,
        "root_dir": str(root_path),
        "depth": max_depth,
        "repo_root": str(repo_root),
        "tree": node,
        "counts": stats,
        "error": None,
    }


def _build_tree_node(path: Path, *, current_depth: int, max_depth: int) -> dict[str, Any]:
    kind = "directory" if path.is_dir() else _file_kind(path.name)
    node: dict[str, Any] = {
        "name": path.name,
        "path": str(path),
        "kind": kind,
    }
    if path.is_dir() and current_depth < max_depth:
        children: list[dict[str, Any]] = []
        for child in sorted(_iter_tree_children(path), key=_tree_sort_key):
            children.append(_build_tree_node(child, current_depth=current_depth + 1, max_depth=max_depth))
        node["children"] = children
    elif path.is_dir():
        node["children"] = []
        node["truncated"] = True
    return node


def _iter_tree_children(path: Path) -> list[Path]:
    children: list[Path] = []
    for child in path.iterdir():
        if child.name in _NOISE_NAMES:
            continue
        children.append(child)
    return children


def _tree_sort_key(path: Path) -> tuple[int, str]:
    if path.is_dir():
        return (0, path.name.lower())
    return (1, path.name.lower())


def _file_kind(name: str) -> str:
    if name == "__init__.py":
        return "package_init"
    if name in _ENTRY_POINT_NAMES:
        return "entry_point"
    return "file"


def _tree_stats(node: dict[str, Any]) -> dict[str, int]:
    directories = 1 if node.get("kind") == "directory" else 0
    files = 1 if node.get("kind") != "directory" else 0
    for child in node.get("children", []) or []:
        child_stats = _tree_stats(child)
        directories += child_stats["directories"]
        files += child_stats["files"]
    return {"directories": directories, "files": files}


def _read_source_file(file_path: Path, *, repo_root: Path) -> dict[str, Any]:
    resolved = file_path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not resolved.is_file():
        raise IsADirectoryError(f"Path is not a file: {file_path}")

    content = resolved.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    line_count = len(lines)
    truncated = False
    if line_count > _MAX_READ_FILE_LINES:
        truncated = True
        head = lines[:_READ_FILE_EDGE_LINES]
        tail = lines[-_READ_FILE_EDGE_LINES:]
        skipped = line_count - (2 * _READ_FILE_EDGE_LINES)
        content = "".join(
            [
                *head,
                f"\n... [truncated {skipped} middle lines] ...\n",
                *tail,
            ]
        )

    return {
        "ok": True,
        "file_path": str(resolved),
        "repo_root": str(repo_root),
        "line_count": line_count,
        "file_size": resolved.stat().st_size,
        "truncated": truncated,
        "content": content,
        "error": None,
    }


def _trace_imports(module_path: Path, *, repo_root: Path) -> dict[str, Any]:
    start_path = module_path.resolve()
    if not start_path.exists():
        raise FileNotFoundError(f"Module not found: {module_path}")
    if start_path.is_dir():
        start_path = start_path / "__init__.py"
    if not start_path.is_file():
        raise IsADirectoryError(f"Path is not a Python source file: {module_path}")

    graph = _build_dependency_graph(start_path, repo_root)
    cycles = _find_cycles(graph["local_edges"])

    return {
        "ok": True,
        "module_path": str(start_path),
        "repo_root": str(repo_root),
        "dependencies": graph["dependencies"],
        "graph": {
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        },
        "cycles": cycles,
        "error": None,
    }


def _build_dependency_graph(start_path: Path, repo_root: Path) -> dict[str, Any]:
    visited: set[Path] = set()
    stack: list[Path] = []
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    local_edges: dict[str, set[str]] = {}
    dependencies: list[dict[str, Any]] = []

    def visit(path: Path) -> None:
        resolved = path.resolve()
        if resolved in visited:
            return
        visited.add(resolved)

        source_text = resolved.read_text(encoding="utf-8")
        tree = ast.parse(source_text, filename=str(resolved))
        node_id = str(resolved)
        nodes[node_id] = {
            "path": node_id,
            "module": _module_name_for_path(resolved, repo_root),
            "imports": [],
        }
        stack.append(resolved)
        for record in _collect_imports(tree, resolved, repo_root):
            nodes[node_id]["imports"].append(record)
            edge = {
                "from": node_id,
                "to": record.get("resolved_path"),
                "import": record["import"],
                "classification": record["classification"],
                "is_relative": record["is_relative"],
            }
            edges.append(edge)
            dependencies.append(record)
            if record["classification"] == "Local" and record.get("resolved_path"):
                target = Path(record["resolved_path"])
                local_edges.setdefault(node_id, set()).add(str(target))
                if target not in stack:
                    visit(target)
        stack.pop()

    visit(start_path)
    for node_id in list(nodes.keys()):
        local_edges.setdefault(node_id, set())
    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "local_edges": local_edges,
        "dependencies": dependencies,
    }


def _collect_imports(tree: ast.AST, source_path: Path, repo_root: Path) -> list[dict[str, Any]]:
    imports: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                imports.append(_classify_import(module_name, source_path, repo_root, is_relative=False, imported_name=alias.asname or alias.name))
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            imports.append(
                _classify_import(
                    module_name,
                    source_path,
                    repo_root,
                    is_relative=node.level > 0,
                    level=node.level,
                    imported_names=[alias.asname or alias.name for alias in node.names],
                )
            )
    return imports


def _classify_import(
    module_name: str,
    source_path: Path,
    repo_root: Path,
    *,
    is_relative: bool,
    level: int = 0,
    imported_name: str | None = None,
    imported_names: list[str] | None = None,
) -> dict[str, Any]:
    imported_names = imported_names or ([] if imported_name is None else [imported_name])
    resolved_path: Path | None = None
    classification = "Third-Party"

    if is_relative:
        resolved_path = _resolve_relative_module(source_path, module_name, level, repo_root)
        if resolved_path is not None:
            classification = "Local"
    else:
        top_level = module_name.split(".", 1)[0] if module_name else ""
        if top_level in sys.builtin_module_names or top_level in getattr(sys, "stdlib_module_names", set()):
            classification = "Standard Library"
        else:
            resolved_path = _resolve_absolute_module(module_name, repo_root)
            if resolved_path is not None:
                classification = "Local"
            else:
                classification = "Third-Party"

    if resolved_path is not None and not resolved_path.exists():
        resolved_path = None

    import_label = module_name or ", ".join(imported_names)
    if imported_names and module_name:
        import_label = f"{module_name}::{', '.join(imported_names)}"
    elif imported_names:
        import_label = ", ".join(imported_names)

    return {
        "import": import_label,
        "module": module_name,
        "imported_names": imported_names,
        "classification": classification,
        "resolved_path": None if resolved_path is None else str(resolved_path),
        "is_relative": is_relative,
        "source_path": str(source_path),
    }


def _resolve_relative_module(source_path: Path, module_name: str, level: int, repo_root: Path) -> Path | None:
    package_dir = source_path.parent
    for _ in range(max(level - 1, 0)):
        package_dir = package_dir.parent
    if module_name:
        candidate = package_dir.joinpath(*module_name.split("."))
    else:
        candidate = package_dir
    return _resolve_candidate_module_path(candidate, repo_root)


def _resolve_absolute_module(module_name: str, repo_root: Path) -> Path | None:
    if not module_name:
        return None
    candidate_parts = module_name.split(".")
    for base_dir in _candidate_local_roots(repo_root):
        candidate = base_dir.joinpath(*candidate_parts)
        resolved = _resolve_candidate_module_path(candidate, repo_root)
        if resolved is not None:
            return resolved
    return None


def _resolve_candidate_module_path(candidate: Path, repo_root: Path) -> Path | None:
    package_init = candidate / "__init__.py"
    if package_init.exists():
        return package_init.resolve()
    module_file = candidate.with_suffix(".py")
    if module_file.exists():
        return module_file.resolve()
    if candidate.exists() and candidate.is_file():
        return candidate.resolve()
    return None


def _candidate_local_roots(repo_root: Path) -> list[Path]:
    roots = [repo_root]
    src_root = repo_root / "src"
    if src_root.exists():
        roots.append(src_root)
    return roots


def _detect_repo_root(start_path: Path, *, base_dir: Path | None) -> Path:
    if base_dir is not None:
        return base_dir.resolve()
    for candidate in [start_path, *start_path.parents]:
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").exists():
            return candidate.resolve()
    return Path.cwd().resolve()


def _module_name_for_path(path: Path, repo_root: Path) -> str:
    try:
        relative = path.resolve().relative_to(repo_root)
    except ValueError:
        return path.stem
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except Exception:
        return False
    return True


def _agent_scoped_roots(agent: Any, *, base_dir: Path | None) -> dict[str, Path]:
    workspace_root = _normalize_agent_root(getattr(agent, "workspace_root", ""), base_dir=base_dir)
    knowledge_root = _normalize_agent_root(getattr(agent, "knowledge_root", ""), base_dir=base_dir or workspace_root)
    roots: dict[str, Path] = {"workspace": workspace_root}
    if knowledge_root != workspace_root:
        roots["knowledge"] = knowledge_root
    else:
        roots["knowledge"] = knowledge_root
    return roots


def _normalize_agent_root(value: str, *, base_dir: Path | None) -> Path:
    text = str(value or "").strip()
    if text:
        root = Path(text).expanduser().resolve()
        if root.exists():
            return root
    if base_dir is not None:
        return Path(base_dir).expanduser().resolve()
    return Path.cwd().resolve()


def _resolve_scoped_path(value: str, roots: dict[str, Path]) -> tuple[Path, Path]:
    requested = Path(value).expanduser()
    ordered_roots = [roots["workspace"], roots["knowledge"]]
    if requested.is_absolute():
        resolved = requested.resolve()
        for root in ordered_roots:
            if _is_within_root(resolved, root):
                return resolved, root
        raise PermissionError(f"Path is outside the agent's designated workspace and knowledge roots: {value}")

    last_candidate = ordered_roots[0] / requested
    for root in ordered_roots:
        candidate = (root / requested).resolve()
        if candidate.exists():
            return candidate, root
        last_candidate = candidate
    return last_candidate, ordered_roots[0]


SOURCE_INSPECTION_PROVIDER_IDS = DEV_TOOLS_PROVIDER_IDS
source_inspection_tool_definitions = dev_tools_tool_definitions
SourceInspectionToolProvider = DevToolsToolProvider
build_source_inspection_tool_providers = build_dev_tools_tool_providers


def _coerce_positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return value


def _find_cycles(local_edges: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()
    path: list[str] = []
    visiting: dict[str, int] = {}
    visited: set[str] = set()

    def dfs(node: str) -> None:
        visited.add(node)
        visiting[node] = len(path)
        path.append(node)
        for neighbor in sorted(local_edges.get(node, set())):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in visiting:
                cycle = path[visiting[neighbor]:] + [neighbor]
                cycle_key = tuple(cycle)
                if cycle_key not in seen_cycles:
                    seen_cycles.add(cycle_key)
                    cycles.append(cycle)
        path.pop()
        visiting.pop(node, None)

    for node in sorted(local_edges):
        if node not in visited:
            dfs(node)
    return cycles


def _error_result(code: str, message: str, **details: Any) -> dict[str, Any]:
    error = {"code": code, "message": message}
    for key, value in details.items():
        if value is not None:
            error[key] = value
    return {"ok": False, "error": error}
