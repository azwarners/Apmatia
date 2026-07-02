from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .templates import (
    ModuleTemplateContext,
    build_module_template_context,
    render_actions_py,
    render_commands_py,
    render_init_py,
    render_manifest_toml,
    render_module_py,
    render_readme_md,
    render_test_py,
    render_tools_py,
    render_views_py,
)
from .workspace import resolve_module_target_dir


MODULE_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class ModuleScaffoldError(ValueError):
    pass


class InvalidModuleSlugError(ModuleScaffoldError):
    pass


class ModuleAlreadyExistsError(ModuleScaffoldError):
    pass


@dataclass(frozen=True, slots=True)
class CreatedModule:
    module_slug: str
    module_dir: Path
    created_files: tuple[Path, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ModuleScaffoldSpec:
    module_slug: str
    module_dir: Path
    files: tuple[Path, ...]


def create_module_scaffold(
    module_slug: str,
    display_name: str,
    description: str = "",
    author: str = "",
    base_dir: Path | None = None,
    workspace: bool = False,
    force: bool = False,
) -> CreatedModule:
    normalized_slug = _validate_module_slug(module_slug)
    module_dir = resolve_module_target_dir(normalized_slug, workspace=workspace, base_dir=base_dir)
    if module_dir.exists() and not force:
        raise ModuleAlreadyExistsError(f"Module already exists: {normalized_slug}")

    context = build_module_template_context(
        module_slug=normalized_slug,
        display_name=display_name,
        description=description,
        author=author,
    )
    spec = build_module_scaffold_spec(context, base_dir=base_dir, workspace=workspace)
    module_dir.mkdir(parents=True, exist_ok=True)

    created_files: list[Path] = []
    for path in spec.files:
        content = _render_scaffold_file(path, context)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not force:
            raise ModuleAlreadyExistsError(f"File already exists: {path}")
        path.write_text(content, encoding="utf-8")
        created_files.append(path)

    return CreatedModule(
        module_slug=normalized_slug,
        module_dir=module_dir,
        created_files=tuple(created_files),
    )


def validate_module_slug(module_slug: str) -> str:
    return _validate_module_slug(module_slug)


def build_module_scaffold_spec(
    context: ModuleTemplateContext,
    base_dir: Path | None = None,
    workspace: bool = False,
) -> ModuleScaffoldSpec:
    module_dir = resolve_module_target_dir(context.module_slug, workspace=workspace, base_dir=base_dir)
    files = (
        module_dir / "__init__.py",
        module_dir / "manifest.toml",
        module_dir / "module.py",
        module_dir / "actions.py",
        module_dir / "tools.py",
        module_dir / "commands.py",
        module_dir / "views.py",
        module_dir / "README.md",
        module_dir / "tests" / f"test_{context.module_slug}_module.py",
    )
    return ModuleScaffoldSpec(module_slug=context.module_slug, module_dir=module_dir, files=files)


def _validate_module_slug(module_slug: str) -> str:
    if module_slug is None:
        raise InvalidModuleSlugError("Module slug cannot be empty.")
    normalized = module_slug.strip()
    if normalized != module_slug:
        raise InvalidModuleSlugError("Module slug cannot contain leading or trailing whitespace.")
    if not normalized:
        raise InvalidModuleSlugError("Module slug cannot be empty.")
    if "/" in normalized or "\\" in normalized or ".." in normalized:
        raise InvalidModuleSlugError("Module slug cannot contain path separators or '..'.")
    if not MODULE_SLUG_PATTERN.fullmatch(normalized):
        raise InvalidModuleSlugError(
            "Module slug must use lowercase letters, numbers, and underscores, and start with a letter."
        )
    return normalized


def _render_scaffold_file(path: Path, context: ModuleTemplateContext) -> str:
    name = path.name
    if name == "__init__.py":
        return render_init_py(context)
    if name == "manifest.toml":
        return render_manifest_toml(context)
    if name == "module.py":
        return render_module_py(context)
    if name == "actions.py":
        return render_actions_py(context)
    if name == "tools.py":
        return render_tools_py(context)
    if name == "commands.py":
        return render_commands_py(context)
    if name == "views.py":
        return render_views_py(context)
    if name == "README.md":
        return render_readme_md(context)
    return render_test_py(context)
