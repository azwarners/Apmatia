from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apmatia.core.modules import (
    ModuleWorkspaceEditor,
    create_module_scaffold,
    ensure_module_workspace_root,
    plan_module_scaffold,
    resolve_module_target_dir,
    validate_module,
)


def workspace_module_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "plan_workspace_module",
            "description": "Preview a draft workspace module scaffold without writing files.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "module_slug": {"type": "string"},
                    "display_name": {"type": "string"},
                    "description": {"type": "string"},
                    "author": {"type": "string"},
                },
                "required": ["module_slug"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": "builtin.plan_workspace_module",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "workspace": True},
        },
        {
            "name": "create_workspace_module",
            "description": "Create a draft workspace module scaffold under workspace/modules.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "module_slug": {"type": "string"},
                    "display_name": {"type": "string"},
                    "description": {"type": "string"},
                    "author": {"type": "string"},
                    "force": {"type": "boolean"},
                },
                "required": ["module_slug", "display_name"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": "builtin.create_workspace_module",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True, "workspace": True},
        },
        {
            "name": "list_workspace_module_files",
            "description": "List files inside a draft workspace module without loading module code.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "module_slug": {"type": "string"},
                },
                "required": ["module_slug"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": "builtin.list_workspace_module_files",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "workspace": True},
        },
        {
            "name": "read_workspace_module_file",
            "description": "Read UTF-8 text from a file inside a draft workspace module.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "module_slug": {"type": "string"},
                    "relative_path": {"type": "string"},
                },
                "required": ["module_slug", "relative_path"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": "builtin.read_workspace_module_file",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "workspace": True},
        },
        {
            "name": "write_workspace_module_file",
            "description": "Write UTF-8 text to a file inside a draft workspace module.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "module_slug": {"type": "string"},
                    "relative_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["module_slug", "relative_path", "content"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": "builtin.write_workspace_module_file",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True, "workspace": True},
        },
        {
            "name": "validate_workspace_module",
            "description": "Validate a draft workspace module scaffold without enabling it.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "module_slug": {"type": "string"},
                },
                "required": ["module_slug"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": "builtin.validate_workspace_module",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "workspace": True},
        },
        ]


@dataclass(slots=True)
class WorkspaceModuleToolProvider:
    provider_id: str
    action: str
    base_dir: Path | None = None

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        if self.action == "plan":
            plan = plan_module_scaffold(
                module_slug=str(arguments["module_slug"]),
                display_name=arguments.get("display_name"),
                description=str(arguments.get("description") or ""),
                author=str(arguments.get("author") or ""),
                base_dir=self.base_dir,
                workspace=True,
            )
            return plan.to_dict()

        workspace_root = ensure_module_workspace_root(self.base_dir)
        if self.action == "create":
            created = create_module_scaffold(
                module_slug=str(arguments["module_slug"]),
                display_name=str(arguments["display_name"]),
                description=str(arguments.get("description") or ""),
                author=str(arguments.get("author") or ""),
                base_dir=self.base_dir,
                workspace=True,
                force=bool(arguments.get("force", False)),
            )
            return {
                "module_slug": created.module_slug,
                "module_dir": str(created.module_dir),
                "created_files": [str(path) for path in created.created_files],
            }

        editor = ModuleWorkspaceEditor(base_dir=self.base_dir)

        if self.action == "list":
            _ = workspace_root
            files = editor.list_files(str(arguments["module_slug"]))
            module_dir = resolve_module_target_dir(str(arguments["module_slug"]), workspace=True, base_dir=self.base_dir)
            return {
                "module_slug": str(arguments["module_slug"]),
                "module_path": str(module_dir),
                "files": [item.to_dict() for item in files],
            }

        if self.action == "read":
            _ = workspace_root
            result = editor.read_file(str(arguments["module_slug"]), str(arguments["relative_path"]))
            return result.to_dict()

        if self.action == "write":
            _ = workspace_root
            result = editor.write_file(
                str(arguments["module_slug"]),
                str(arguments["relative_path"]),
                str(arguments.get("content") or ""),
            )
            payload = result.to_dict()
            payload["suggested_next_command"] = _validate_suggestion(result.relative_path, result.module_slug)
            return payload

        if self.action == "validate":
            _ = workspace_root
            result = validate_module(str(arguments["module_slug"]), base_dir=self.base_dir, workspace=True)
            return result.to_dict()

        raise ValueError(f"Unsupported workspace module tool action: {self.action}")


def build_workspace_module_tool_providers(base_dir: Path | None = None) -> list[WorkspaceModuleToolProvider]:
    return [
        WorkspaceModuleToolProvider("builtin.plan_workspace_module", "plan", base_dir=base_dir),
        WorkspaceModuleToolProvider("builtin.create_workspace_module", "create", base_dir=base_dir),
        WorkspaceModuleToolProvider("builtin.list_workspace_module_files", "list", base_dir=base_dir),
        WorkspaceModuleToolProvider("builtin.read_workspace_module_file", "read", base_dir=base_dir),
        WorkspaceModuleToolProvider("builtin.write_workspace_module_file", "write", base_dir=base_dir),
        WorkspaceModuleToolProvider("builtin.validate_workspace_module", "validate", base_dir=base_dir),
    ]


def _validate_suggestion(relative_path: str, module_slug: str) -> str:
    if relative_path.endswith(".py") or relative_path.endswith("manifest.toml"):
        return f"apmatia module validate {module_slug} --workspace"
    return ""
