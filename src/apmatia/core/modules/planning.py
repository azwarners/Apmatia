from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from .scaffold import ModuleScaffoldError, build_module_scaffold_spec, validate_module_slug
from .templates import build_module_template_context
from .workspace import resolve_module_target_dir


@dataclass(frozen=True, slots=True)
class ModuleScaffoldPlan:
    module_slug: str
    display_name: str
    description: str
    author: str
    module_path: Path
    files: tuple[Path, ...]
    target_exists: bool
    passed: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    suggested_next_command: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_slug": self.module_slug,
            "display_name": self.display_name,
            "description": self.description,
            "author": self.author,
            "module_path": str(self.module_path),
            "files": [str(path) for path in self.files],
            "target_exists": self.target_exists,
            "passed": self.passed,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "suggested_next_command": self.suggested_next_command,
        }


def plan_module_scaffold(
    module_slug: str,
    display_name: str | None = None,
    description: str = "",
    author: str = "",
    base_dir: Path | None = None,
    workspace: bool = False,
) -> ModuleScaffoldPlan:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        normalized_slug = validate_module_slug(module_slug)
    except ModuleScaffoldError as exc:
        normalized_slug = module_slug
        errors.append(str(exc))

    resolved_display_name = display_name or _titleize_slug(normalized_slug)
    module_dir = resolve_module_target_dir(normalized_slug, workspace=workspace, base_dir=base_dir)
    target_exists = module_dir.exists()
    files: tuple[Path, ...] = ()

    if not errors:
        context = build_module_template_context(
            module_slug=normalized_slug,
            display_name=resolved_display_name,
            description=description,
            author=author,
        )
        spec = build_module_scaffold_spec(context, base_dir=base_dir, workspace=workspace)
        files = spec.files

    if target_exists:
        warnings.append("target module path already exists")

    if errors:
        suggested_next_command = ""
    elif target_exists:
        suggested_next_command = f"apmatia module validate {normalized_slug}{' --workspace' if workspace else ''}"
    else:
        next_command = f"apmatia module create {normalized_slug} --name {json.dumps(resolved_display_name)}"
        if workspace:
            next_command += " --workspace"
        suggested_next_command = next_command

    return ModuleScaffoldPlan(
        module_slug=normalized_slug,
        display_name=resolved_display_name,
        description=description,
        author=author,
        module_path=module_dir,
        files=files,
        target_exists=target_exists,
        passed=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        suggested_next_command=suggested_next_command,
    )


def serialize_module_scaffold_plan(plan: ModuleScaffoldPlan) -> dict[str, Any]:
    return plan.to_dict()


def _titleize_slug(module_slug: str) -> str:
    if not module_slug:
        return "Module"
    return module_slug.replace("_", " ").strip().title() or "Module"
