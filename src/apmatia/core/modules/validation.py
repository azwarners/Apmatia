from __future__ import annotations

import builtins
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

from apmatia.core.registry import Registry

from .manifest import ModuleManifest, load_module_manifest
from .scaffold import validate_module_slug
from .workspace import resolve_module_target_dir


REQUIRED_FILES = (
    "__init__.py",
    "manifest.toml",
    "module.py",
    "actions.py",
    "tools.py",
    "commands.py",
    "views.py",
    "README.md",
)

VALIDATED_PYTHON_FILES = (
    "__init__.py",
    "module.py",
    "actions.py",
    "tools.py",
    "commands.py",
    "views.py",
)


@dataclass(frozen=True, slots=True)
class ModuleValidationCheck:
    name: str
    passed: bool
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ModuleValidationResult:
    module_slug: str
    module_path: Path
    passed: bool
    checks: tuple[ModuleValidationCheck, ...]
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    manifest: ModuleManifest | None = None
    registered: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_slug": self.module_slug,
            "module_path": str(self.module_path),
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "manifest": _manifest_to_dict(self.manifest),
            "registered": dict(self.registered),
        }


def validate_module(
    slug: str,
    base_dir: Path | None = None,
    *,
    workspace: bool = False,
) -> ModuleValidationResult:
    module_slug = validate_module_slug(slug)
    module_dir = resolve_module_target_dir(module_slug, workspace=workspace, base_dir=base_dir)
    checks: list[ModuleValidationCheck] = []
    errors: list[str] = []
    warnings: list[str] = []
    manifest: ModuleManifest | None = None
    registered: dict[str, list[str]] = {}
    streamlit_checked = False
    streamlit_safe = False

    existing_files = {name: module_dir / name for name in REQUIRED_FILES}
    required_files_ok = True
    for file_name, path in existing_files.items():
        if path.exists():
            checks.append(ModuleValidationCheck(name=f"required file: {file_name}", passed=True))
        else:
            required_files_ok = False
            message = f"missing required file: {file_name}"
            checks.append(ModuleValidationCheck(name=f"required file: {file_name}", passed=False, message=message))
            errors.append(message)

    if existing_files["manifest.toml"].exists():
        try:
            manifest = load_module_manifest(module_dir)
            checks.append(ModuleValidationCheck(name="manifest parses", passed=True))
        except Exception as exc:
            message = f"manifest.toml failed to parse: {exc}"
            checks.append(ModuleValidationCheck(name="manifest parses", passed=False, message=message))
            errors.append(message)
    else:
        checks.append(
            ModuleValidationCheck(
                name="manifest parses",
                passed=False,
                message="manifest.toml missing; parse skipped",
            )
        )

    if manifest is not None:
        module_id_matches = manifest.module_id == module_slug
        if module_id_matches:
            checks.append(ModuleValidationCheck(name="manifest id matches slug", passed=True))
        else:
            message = f"manifest module_id '{manifest.module_id}' does not match slug '{module_slug}'"
            checks.append(ModuleValidationCheck(name="manifest id matches slug", passed=False, message=message))
            errors.append(message)

        manifest_type_errors = _validate_manifest_metadata(manifest)
        checks.extend(manifest_type_errors.checks)
        errors.extend(manifest_type_errors.errors)

    syntax_results: dict[str, bool] = {}
    for file_name in VALIDATED_PYTHON_FILES:
        path = module_dir / file_name
        check_name = f"python syntax: {file_name}"
        if not path.exists():
            syntax_results[file_name] = False
            checks.append(ModuleValidationCheck(name=check_name, passed=False, message=f"missing file: {file_name}"))
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            syntax_results[file_name] = True
            checks.append(ModuleValidationCheck(name=check_name, passed=True))
        except SyntaxError as exc:
            syntax_results[file_name] = False
            message = f"{file_name} has invalid syntax: {exc.msg}"
            checks.append(ModuleValidationCheck(name=check_name, passed=False, message=message))
            errors.append(message)

    module_py_path = module_dir / "module.py"
    if module_py_path.exists() and syntax_results.get("module.py", False):
        module_name = f"apmatia_validation_{module_slug}_{uuid4().hex}"
        try:
            module = _load_module_without_streamlit(module_py_path, module_name)
            streamlit_checked = True
            streamlit_safe = True
            if not hasattr(module, "register") or not callable(getattr(module, "register")):
                message = "module.py does not expose register(registry)"
                checks.append(ModuleValidationCheck(name="register(registry) exists", passed=False, message=message))
                errors.append(message)
            else:
                checks.append(ModuleValidationCheck(name="register(registry) exists", passed=True))
                try:
                    fresh_registry = Registry()
                    module.register(fresh_registry)
                    registered = {
                        "modules": [item.module_id for item in fresh_registry.list_modules()],
                        "actions": [item.action_id for item in fresh_registry.list_actions()],
                        "tools": [item.tool_id for item in fresh_registry.list_tools()],
                        "commands": [item.command_id for item in fresh_registry.list_commands()],
                        "views": [item.view_id for item in fresh_registry.list_views()],
                    }
                    if fresh_registry.list_modules():
                        checks.append(ModuleValidationCheck(name="register(registry) succeeds", passed=True))
                        checks.append(ModuleValidationCheck(name="registry contributions are valid", passed=True))
                    else:
                        message = "register(registry) did not register module metadata"
                        checks.append(ModuleValidationCheck(name="register(registry) succeeds", passed=False, message=message))
                        errors.append(message)
                except Exception as exc:
                    message = f"register(registry) raised an exception: {exc}"
                    checks.append(ModuleValidationCheck(name="register(registry) succeeds", passed=False, message=message))
                    errors.append(message)
        except Exception as exc:
            message = f"module.py could not be imported: {exc}"
            checks.append(ModuleValidationCheck(name="register(registry) exists", passed=False, message=message))
            errors.append(message)

    if streamlit_checked:
        if streamlit_safe:
            checks.append(ModuleValidationCheck(name="streamlit import not required", passed=True))
        else:
            message = "module files imported or required streamlit"
            checks.append(ModuleValidationCheck(name="streamlit import not required", passed=False, message=message))
            errors.append(message)

    passed = not errors and required_files_ok and manifest is not None
    if manifest is None:
        passed = False

    if not required_files_ok:
        warnings.append("validation stopped short of some checks because required files were missing")

    return ModuleValidationResult(
        module_slug=module_slug,
        module_path=module_dir,
        passed=passed,
        checks=tuple(checks),
        errors=tuple(errors),
        warnings=tuple(warnings),
        manifest=manifest,
        registered=registered,
    )


def serialize_module_validation_result(result: ModuleValidationResult) -> dict[str, Any]:
    return result.to_dict()


def _load_module_without_streamlit(module_path: Path, module_name: str) -> ModuleType:
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "streamlit" or name.startswith("streamlit."):
            raise ImportError("streamlit import attempted during validation")
        return original_import(name, *args, **kwargs)

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    previous_import = builtins.__import__
    try:
        builtins.__import__ = guarded_import
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    finally:
        builtins.__import__ = previous_import
        sys.modules.pop(module_name, None)
    return module


def _manifest_to_dict(manifest: ModuleManifest | None) -> dict[str, Any] | None:
    if manifest is None:
        return None
    return {
        "module_id": manifest.module_id,
        "name": manifest.name,
        "version": manifest.version,
        "description": manifest.description,
        "author": manifest.author,
        "metadata": dict(manifest.metadata),
        "dependencies": dict(manifest.dependencies),
    }


@dataclass(frozen=True, slots=True)
class _ManifestValidationOutcome:
    checks: tuple[ModuleValidationCheck, ...]
    errors: tuple[str, ...]


def _validate_manifest_metadata(manifest: ModuleManifest) -> _ManifestValidationOutcome:
    checks: list[ModuleValidationCheck] = []
    errors: list[str] = []

    metadata = manifest.metadata if isinstance(manifest.metadata, dict) else {}
    dependencies = manifest.dependencies if isinstance(manifest.dependencies, dict) else {}

    checks.extend(_validate_optional_string(metadata, "metadata.category", errors))
    checks.extend(_validate_optional_string_list(metadata, "metadata.tags", errors))
    checks.extend(_validate_optional_string(dependencies, "dependencies.python", errors))
    checks.extend(_validate_optional_string_list(dependencies, "dependencies.python_packages", errors))
    checks.extend(_validate_optional_string_list(dependencies, "dependencies.system_packages", errors))
    checks.extend(_validate_optional_string_list(dependencies, "dependencies.modules", errors))
    checks.extend(_validate_optional_string_list(dependencies, "dependencies.tools", errors))

    return _ManifestValidationOutcome(checks=tuple(checks), errors=tuple(errors))


def _validate_optional_string(container: dict[str, Any], dotted_name: str, errors: list[str]) -> tuple[ModuleValidationCheck, ...]:
    key = dotted_name.split(".")[-1]
    if key not in container:
        return ()
    value = container[key]
    if isinstance(value, str):
        return (ModuleValidationCheck(name=f"{dotted_name} is a string", passed=True),)
    message = f"{dotted_name} must be a string"
    errors.append(message)
    return (ModuleValidationCheck(name=f"{dotted_name} is a string", passed=False, message=message),)


def _validate_optional_string_list(container: dict[str, Any], dotted_name: str, errors: list[str]) -> tuple[ModuleValidationCheck, ...]:
    key = dotted_name.split(".")[-1]
    if key not in container:
        return ()
    value = container[key]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return (ModuleValidationCheck(name=f"{dotted_name} is a list of strings", passed=True),)
    message = f"{dotted_name} must be a list of strings"
    errors.append(message)
    return (ModuleValidationCheck(name=f"{dotted_name} is a list of strings", passed=False, message=message),)
