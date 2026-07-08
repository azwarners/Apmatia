from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apmatia.core.runtime_paths import get_app_dir

KNOWLEDGE_PROVIDER_IDS = {
    "readme_first": "builtin.apmatia_knowledge_readme_first",
    "tree": "builtin.apmatia_knowledge_tree",
    "read": "builtin.apmatia_knowledge_read",
}

_DEFAULT_TREE_DEPTH: int | None = None
_MAX_READ_FILE_LINES = 1000
_READ_FILE_EDGE_LINES = 50
_TREE_MODES = {"directories", "directories_and_files"}


def knowledge_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "apmatia_knowledge_readme_first",
            "description": (
                "Read this first. Return the exact knowledge workspace location, accepted path aliases, "
                "and usage guidance for the knowledge tools."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": KNOWLEDGE_PROVIDER_IDS["readme_first"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "module": "apmatia_knowledge", "tool": "readme_first"},
        },
        {
            "name": "apmatia_knowledge_tree",
            "description": (
                "Return a JSON tree for the knowledge workspace using paths relative to the knowledge root "
                "with optional depth and file visibility controls. Paths like '.', '/', '/knowledge', "
                "'/knowledge/docs', or 'docs' are normalized to the same workspace root."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "default": ".",
                        "description": "Path relative to the knowledge root. '/', '/knowledge', and 'knowledge/' are treated as root aliases.",
                    },
                    "depth": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Maximum depth below the requested path.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["directories", "directories_and_files"],
                        "default": "directories_and_files",
                        "description": "Whether to include only directories or both directories and files.",
                    },
                },
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": KNOWLEDGE_PROVIDER_IDS["tree"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "module": "apmatia_knowledge", "tool": "tree"},
        },
        {
            "name": "apmatia_knowledge_read",
            "description": "Read a UTF-8 file from the knowledge workspace using a path relative to the knowledge root. '/', '/knowledge', and '/knowledge/...' are normalized for convenience.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path relative to the knowledge root. Root aliases like '/' and '/knowledge' are accepted.",
                    },
                },
                "required": ["file_path"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": KNOWLEDGE_PROVIDER_IDS["read"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "module": "apmatia_knowledge", "tool": "read"},
        },
    ]


@dataclass(slots=True)
class KnowledgeToolProvider:
    provider_id: str
    action: str
    base_dir: Path | None = None

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        try:
            if self.action == "readme_first":
                return _knowledge_info(base_dir=self.base_dir)
            if self.action == "tree":
                return _inspect_knowledge_tree(
                    str(arguments.get("path") or "."),
                    depth=arguments.get("depth"),
                    mode=str(arguments.get("mode") or "directories_and_files"),
                    base_dir=self.base_dir,
                )
            if self.action == "read":
                return _read_knowledge_file(str(arguments["file_path"]), base_dir=self.base_dir)
            raise ValueError(f"Unsupported knowledge action: {self.action}")
        except (FileNotFoundError, NotADirectoryError, IsADirectoryError, ValueError) as exc:
            return _error_result("KNOWLEDGE_ERROR", str(exc), action=self.action)
        except Exception as exc:  # pragma: no cover - defensive guard
            return _error_result(
                "KNOWLEDGE_ERROR",
                str(exc),
                action=self.action,
                exception_type=type(exc).__name__,
            )


def build_knowledge_tool_providers(base_dir: Path | None = None) -> list[KnowledgeToolProvider]:
    return [
        KnowledgeToolProvider(KNOWLEDGE_PROVIDER_IDS["readme_first"], "readme_first", base_dir=base_dir),
        KnowledgeToolProvider(KNOWLEDGE_PROVIDER_IDS["tree"], "tree", base_dir=base_dir),
        KnowledgeToolProvider(KNOWLEDGE_PROVIDER_IDS["read"], "read", base_dir=base_dir),
    ]


def knowledge_base_dir(base_dir: Path | None = None) -> Path:
    return Path(base_dir or get_app_dir()).expanduser()


def knowledge_root(base_dir: Path | None = None) -> Path:
    return knowledge_base_dir(base_dir) / "workspace" / "knowledge"


def _knowledge_info(*, base_dir: Path | None) -> dict[str, Any]:
    root = knowledge_root(base_dir)
    return {
        "ok": True,
        "base_dir": str(knowledge_base_dir(base_dir)),
        "knowledge_root": str(root),
        "root_aliases": [".", "/", "/knowledge", "knowledge", "knowledge/", "/knowledge/"],
        "accepted_path_form": "Relative to the knowledge root. Leading /knowledge or / are normalized to the knowledge workspace.",
        "tools": [
            {
                "name": "apmatia_knowledge_readme_first",
                "purpose": "Show the exact root and path rules.",
            },
            {
                "name": "apmatia_knowledge_tree",
                "purpose": "Inspect folders and optionally list files.",
                "arguments": {
                    "path": "Knowledge-relative path, default '.'",
                    "depth": "Non-negative integer depth limit",
                    "mode": "directories or directories_and_files",
                },
            },
            {
                "name": "apmatia_knowledge_read",
                "purpose": "Read a UTF-8 file by knowledge-relative path.",
                "arguments": {
                    "file_path": "Knowledge-relative file path",
                },
            },
        ],
        "examples": [
            {"tool": "apmatia_knowledge_tree", "args": {"path": "."}},
            {"tool": "apmatia_knowledge_tree", "args": {"path": "/knowledge", "mode": "directories_and_files", "depth": 3}},
            {"tool": "apmatia_knowledge_read", "args": {"file_path": "/knowledge/README.md"}},
        ],
        "error": None,
    }


def _inspect_knowledge_tree(path: str, *, depth: Any, mode: str, base_dir: Path | None) -> dict[str, Any]:
    if mode not in _TREE_MODES:
        raise ValueError(f"mode must be one of: {', '.join(sorted(_TREE_MODES))}.")

    root = knowledge_root(base_dir)
    target, relative_path = _resolve_knowledge_path(path, base_dir=base_dir)
    if not target.exists():
        raise FileNotFoundError(_missing_path_message(path, root, kind="directory"))
    if not target.is_dir():
        raise NotADirectoryError(_wrong_kind_message(path, root, kind="directory"))

    max_depth = _DEFAULT_TREE_DEPTH if depth is None else _coerce_non_negative_int(depth, field_name="depth")
    include_files = mode == "directories_and_files"
    node = _build_tree_node(target, current_depth=0, max_depth=max_depth, include_files=include_files)

    return {
        "ok": True,
        "base_dir": str(knowledge_base_dir(base_dir)),
        "knowledge_root": str(root),
        "path": str(target),
        "relative_path": relative_path,
        "normalized_path": relative_path,
        "mode": mode,
        "depth": max_depth,
        "tree": node,
        "counts": _tree_stats(node),
        "error": None,
    }


def _build_tree_node(
    path: Path,
    *,
    current_depth: int,
    max_depth: int | None,
    include_files: bool,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "name": path.name,
        "path": str(path),
        "kind": "directory" if path.is_dir() else "file",
    }
    if path.is_dir():
        if max_depth is not None and current_depth >= max_depth:
            node["children"] = []
            node["truncated"] = True
            return node

        children: list[dict[str, Any]] = []
        for child in sorted(path.iterdir(), key=_tree_sort_key):
            if child.is_dir():
                children.append(
                    _build_tree_node(
                        child,
                        current_depth=current_depth + 1,
                        max_depth=max_depth,
                        include_files=include_files,
                    )
                )
            elif include_files:
                children.append(
                    {
                        "name": child.name,
                        "path": str(child),
                        "kind": "file",
                    }
                )
        node["children"] = children
    return node


def _tree_sort_key(path: Path) -> tuple[int, str]:
    if path.is_dir():
        return (0, path.name.lower())
    return (1, path.name.lower())


def _tree_stats(node: dict[str, Any]) -> dict[str, int]:
    directories = 1 if node.get("kind") == "directory" else 0
    files = 1 if node.get("kind") == "file" else 0
    for child in node.get("children", []) or []:
        child_stats = _tree_stats(child)
        directories += child_stats["directories"]
        files += child_stats["files"]
    return {"directories": directories, "files": files}


def _read_knowledge_file(file_path: str, *, base_dir: Path | None) -> dict[str, Any]:
    resolved, relative_path = _resolve_knowledge_path(file_path, base_dir=base_dir)
    root = knowledge_root(base_dir)
    if not resolved.exists():
        raise FileNotFoundError(_missing_path_message(file_path, root, kind="file"))
    if not resolved.is_file():
        raise IsADirectoryError(_wrong_kind_message(file_path, root, kind="file"))

    try:
        content = resolved.read_text(encoding="utf-8")
        decoded_with_replacements = False
    except UnicodeDecodeError:
        content = resolved.read_text(encoding="utf-8", errors="replace")
        decoded_with_replacements = True

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
        "base_dir": str(knowledge_base_dir(base_dir)),
        "knowledge_root": str(knowledge_root(base_dir)),
        "file_path": str(resolved),
        "relative_path": relative_path,
        "normalized_path": relative_path,
        "line_count": line_count,
        "file_size": resolved.stat().st_size,
        "truncated": truncated,
        "decoded_with_replacements": decoded_with_replacements,
        "content": content,
        "error": None,
    }


def _resolve_knowledge_path(value: str, *, base_dir: Path | None) -> tuple[Path, str]:
    root = knowledge_root(base_dir).resolve()
    raw_path = Path(value).expanduser()
    relative_path = _normalize_relative_knowledge_path(raw_path, root=root, original_value=value)
    resolved = (root / relative_path).resolve()
    if not _is_within_root(resolved, root):
        raise ValueError(_invalid_path_message(value, root))
    return resolved, relative_path


def _normalize_relative_knowledge_path(path: Path, *, root: Path, original_value: str) -> str:
    text = original_value.strip()
    if not text or text in {".", "/"}:
        return "."

    if path.is_absolute():
        if _is_within_root(path, root):
            relative = path.resolve().relative_to(root)
        else:
            relative = Path(*path.parts[1:])
    else:
        relative = path

    parts = list(relative.parts)
    if parts[:2] == ["workspace", "knowledge"]:
        parts = parts[2:]
    elif parts[:1] == ["knowledge"] and (path.is_absolute() or text.startswith("knowledge/") or text == "knowledge"):
        parts = parts[1:]
    elif path.is_absolute() and not parts and text == "/":
        return "."

    normalized_parts: list[str] = []
    for part in parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not normalized_parts:
                raise ValueError(_invalid_path_message(original_value, root))
            normalized_parts.pop()
            continue
        normalized_parts.append(part)

    normalized = Path(*normalized_parts)
    if str(normalized) == ".":
        return "."
    return str(normalized)


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except Exception:
        return False
    return True


def _coerce_non_negative_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValueError(f"{field_name} must be greater than or equal to zero.")
    return value


def _invalid_path_message(value: str, root: Path) -> str:
    return (
        "Path must be relative to the knowledge root "
        f"({root}). Got: {value!r}. Use '.', '/', '/knowledge', or a relative path like 'docs/notes.txt'."
    )


def _missing_path_message(value: str, root: Path, *, kind: str) -> str:
    label = "directory" if kind == "directory" else "file"
    return (
        f"Knowledge {label} not found under {root}: {value!r}. "
        "Pass a path relative to the knowledge root, such as 'docs' or 'docs/notes.txt'."
    )


def _wrong_kind_message(value: str, root: Path, *, kind: str) -> str:
    label = "directory" if kind == "directory" else "file"
    other = "file" if kind == "directory" else "directory"
    return (
        f"Knowledge path is not a {label} under {root}: {value!r}. "
        f"Expected a relative {label} path, not a {other} path."
    )


def _error_result(code: str, message: str, **details: Any) -> dict[str, Any]:
    error = {"code": code, "message": message}
    for key, value in details.items():
        if value is not None:
            error[key] = value
    return {"ok": False, "error": error}
