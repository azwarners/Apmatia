from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from apmatia.core.modules import (
    ModuleAlreadyExistsError,
    ModuleScaffoldError,
    ModuleWorkspaceEditor,
    get_bundled_module_inspection,
    list_bundled_module_inspections,
    list_workspace_module_inspections,
    plan_module_scaffold,
    serialize_module_scaffold_plan,
    serialize_module_inspection,
    serialize_module_inspections,
    serialize_module_validation_result,
    create_module_scaffold,
    get_workspace_module_inspection,
    WorkspaceEditorError,
    WorkspacePathError,
    WorkspaceFileNotFoundError,
    WorkspaceModuleNotFoundError,
    validate_module,
)


def add_module_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    module_parser = subparsers.add_parser("module", help="Module scaffolding commands.")
    module_subparsers = module_parser.add_subparsers(dest="module_command", required=True)

    create_parser = module_subparsers.add_parser("create", help="Create a new module scaffold.")
    create_parser.add_argument("module_slug", help="Module slug such as productivity.")
    create_parser.add_argument("--name", required=True, help="Display name for the module.")
    create_parser.add_argument("--description", default="", help="Short module description.")
    create_parser.add_argument("--author", default="", help="Module author.")
    create_parser.add_argument("--base-dir", default=None, help="Base directory for the scaffold.")
    create_parser.add_argument("--workspace", action="store_true", help="Create the module in the draft workspace.")
    create_parser.add_argument("--force", action="store_true", help="Overwrite an existing scaffold.")
    create_parser.set_defaults(handler=handle_module_create)

    plan_parser = module_subparsers.add_parser("plan", help="Preview a module scaffold.")
    plan_parser.add_argument("module_slug", help="Module slug such as productivity.")
    plan_parser.add_argument("--name", default=None, help="Display name for the module.")
    plan_parser.add_argument("--description", default="", help="Short module description.")
    plan_parser.add_argument("--author", default="", help="Module author.")
    plan_parser.add_argument("--base-dir", default=None, help="Base directory for the scaffold preview.")
    plan_parser.add_argument("--workspace", action="store_true", help="Preview the draft workspace location.")
    plan_parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    plan_parser.set_defaults(handler=handle_module_plan)

    list_parser = module_subparsers.add_parser("list", help="List bundled or workspace modules.")
    list_parser.add_argument("--base-dir", default=None, help="Base directory for module inspection.")
    list_parser.add_argument("--workspace", action="store_true", help="List draft workspace modules.")
    list_parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    list_parser.set_defaults(handler=handle_module_list)

    show_parser = module_subparsers.add_parser("show", help="Show a bundled or workspace module.")
    show_parser.add_argument("module_slug", help="Module slug such as productivity.")
    show_parser.add_argument("--base-dir", default=None, help="Base directory for module inspection.")
    show_parser.add_argument("--workspace", action="store_true", help="Show a draft workspace module.")
    show_parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    show_parser.set_defaults(handler=handle_module_show)

    validate_parser = module_subparsers.add_parser("validate", help="Validate a bundled or generated module.")
    validate_parser.add_argument("module_slug", help="Module slug such as productivity.")
    validate_parser.add_argument("--base-dir", default=None, help="Base directory for module validation.")
    validate_parser.add_argument("--workspace", action="store_true", help="Validate a draft workspace module.")
    validate_parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    validate_parser.set_defaults(handler=handle_module_validate)

    files_parser = module_subparsers.add_parser("files", help="List files in a workspace module.")
    files_parser.add_argument("module_slug", help="Module slug such as productivity.")
    files_parser.add_argument("--base-dir", default=None, help="Base directory for workspace inspection.")
    files_parser.add_argument("--workspace", action="store_true", help="Inspect a workspace module.")
    files_parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    files_parser.set_defaults(handler=handle_module_files)

    read_parser = module_subparsers.add_parser("read", help="Read a file from a workspace module.")
    read_parser.add_argument("module_slug", help="Module slug such as productivity.")
    read_parser.add_argument("relative_path", help="Relative path inside the workspace module.")
    read_parser.add_argument("--base-dir", default=None, help="Base directory for workspace inspection.")
    read_parser.add_argument("--workspace", action="store_true", help="Inspect a workspace module.")
    read_parser.set_defaults(handler=handle_module_read)

    write_parser = module_subparsers.add_parser("write", help="Write a file in a workspace module.")
    write_parser.add_argument("module_slug", help="Module slug such as productivity.")
    write_parser.add_argument("relative_path", help="Relative path inside the workspace module.")
    write_parser.add_argument("--base-dir", default=None, help="Base directory for workspace inspection.")
    write_parser.add_argument("--workspace", action="store_true", help="Write to a workspace module.")
    write_parser.add_argument("--stdin", action="store_true", help="Read file content from stdin.")
    write_parser.set_defaults(handler=handle_module_write)


def handle_module_create(args: argparse.Namespace) -> int:
    try:
        created = create_module_scaffold(
            module_slug=args.module_slug,
            display_name=args.name,
            description=args.description,
            author=args.author,
            base_dir=Path(args.base_dir) if args.base_dir else None,
            workspace=bool(args.workspace),
            force=bool(args.force),
        )
    except (ModuleAlreadyExistsError, ModuleScaffoldError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Created module scaffold at {created.module_dir}")
    print("Created files:")
    for path in created.created_files:
        print(f"- {path}")
    return 0


def handle_module_list(args: argparse.Namespace) -> int:
    base_dir = Path(args.base_dir) if args.base_dir else None
    inspections = (
        list_workspace_module_inspections(base_dir=base_dir) if args.workspace else list_bundled_module_inspections(base_dir=base_dir)
    )
    if not inspections:
        print("No workspace modules found." if args.workspace else "No bundled modules found.")
        return 0

    if args.format == "json":
        payload = serialize_module_inspections(inspections)
        print(json.dumps(payload, indent=2))
        return 0

    for inspection in inspections:
        manifest = inspection.manifest
        description = f" - {manifest.description}" if manifest.description else ""
        prefix = f"{inspection.source} | " if args.workspace else ""
        print(f"{prefix}{manifest.module_id} | {manifest.name} | {manifest.version}{description}")
    return 0


def handle_module_show(args: argparse.Namespace) -> int:
    base_dir = Path(args.base_dir) if args.base_dir else None
    inspection = (
        get_workspace_module_inspection(args.module_slug, base_dir=base_dir)
        if args.workspace
        else get_bundled_module_inspection(args.module_slug, base_dir=base_dir)
    )
    if inspection is None:
        print(f"Error: module not found: {args.module_slug}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(serialize_module_inspection(inspection), indent=2))
        return 0

    manifest = inspection.manifest
    if inspection.source != "bundled":
        print(f"Source: {inspection.source}")
    print(f"Module: {manifest.module_id}")
    print(f"Name: {manifest.name}")
    print(f"Version: {manifest.version}")
    print(f"Description: {manifest.description or ''}")
    print(f"Author: {manifest.author or ''}")
    print(f"Status: {manifest.status.value}")
    print(f"Category: {manifest.category.value}")
    print(f"Default Enabled: {manifest.default_enabled}")
    print(f"Tags: {_join_strings(manifest.tags)}")
    print(f"Metadata: {manifest.metadata}")
    print("Dependencies:")
    print(f"  Python: {manifest.dependencies.get('python', '')}")
    print(f"  Python Packages: {_join_strings(manifest.dependencies.get('python_packages', []))}")
    print(f"  System Packages: {_join_strings(manifest.dependencies.get('system_packages', []))}")
    print(f"  Modules: {_join_strings(manifest.dependencies.get('modules', []))}")
    print(f"  Tools: {_join_strings(manifest.dependencies.get('tools', []))}")
    print(f"Actions: {', '.join(inspection.actions) if inspection.actions else ''}")
    print(f"Tools: {', '.join(inspection.tools) if inspection.tools else ''}")
    print(f"Commands: {', '.join(inspection.commands) if inspection.commands else ''}")
    print(f"Views: {', '.join(inspection.views) if inspection.views else ''}")
    return 0


def handle_module_validate(args: argparse.Namespace) -> int:
    try:
        result = validate_module(
            args.module_slug,
            base_dir=Path(args.base_dir) if args.base_dir else None,
            workspace=bool(args.workspace),
        )
    except ModuleScaffoldError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(serialize_module_validation_result(result), indent=2))
    else:
        _print_module_validation_text(result)
    return 0 if result.passed else 1


def handle_module_files(args: argparse.Namespace) -> int:
    if not args.workspace:
        print("Error: module files only supports workspace modules. Use --workspace.", file=sys.stderr)
        return 1

    editor = ModuleWorkspaceEditor(base_dir=Path(args.base_dir) if args.base_dir else None)
    try:
        files = editor.list_files(args.module_slug)
    except WorkspaceEditorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps([item.to_dict() for item in files], indent=2))
        return 0

    if not files:
        print("No files found.")
        return 0

    for item in files:
        print(f"{item.relative_path} | {item.size_bytes} bytes | {item.path}")
    return 0


def handle_module_read(args: argparse.Namespace) -> int:
    if not args.workspace:
        print("Error: module read only supports workspace modules. Use --workspace.", file=sys.stderr)
        return 1

    editor = ModuleWorkspaceEditor(base_dir=Path(args.base_dir) if args.base_dir else None)
    try:
        result = editor.read_file(args.module_slug, args.relative_path)
    except (WorkspaceEditorError, WorkspacePathError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(result.content, end="" if result.content.endswith("\n") else "\n")
    return 0


def handle_module_write(args: argparse.Namespace) -> int:
    if not args.workspace:
        print("Error: module write only supports workspace modules. Use --workspace.", file=sys.stderr)
        return 1
    if not args.stdin:
        print("Error: module write requires --stdin.", file=sys.stderr)
        return 1

    if bool(getattr(sys.stdin, "isatty", lambda: False)()):
        print("Error: module write requires piped stdin content.", file=sys.stderr)
        return 1

    stdin_reader = getattr(sys.stdin, "read", None)
    if stdin_reader is None:
        print("Error: stdin is not readable.", file=sys.stderr)
        return 1

    content = stdin_reader()

    editor = ModuleWorkspaceEditor(base_dir=Path(args.base_dir) if args.base_dir else None)
    try:
        result = editor.write_file(args.module_slug, args.relative_path, content)
    except (WorkspaceEditorError, WorkspacePathError, WorkspaceModuleNotFoundError, WorkspaceFileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Wrote {result.module_slug}:{result.relative_path} "
        f"({result.bytes_written} bytes) at {result.path}"
    )
    if result.relative_path.endswith(".py") or result.relative_path.endswith("manifest.toml"):
        print(f"Suggested next command: apmatia module validate {result.module_slug} --workspace")
    return 0


def handle_module_plan(args: argparse.Namespace) -> int:
    plan = plan_module_scaffold(
        module_slug=args.module_slug,
        display_name=args.name,
        description=args.description,
        author=args.author,
        base_dir=Path(args.base_dir) if args.base_dir else None,
        workspace=bool(args.workspace),
    )
    if not plan.passed and plan.errors:
        print(f"Error: {plan.errors[0]}", file=sys.stderr)
    if args.format == "json":
        print(json.dumps(serialize_module_scaffold_plan(plan), indent=2))
    else:
        _print_module_plan_text(plan)
    return 0 if plan.passed else 1


def _print_module_validation_text(result) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(f"Module: {result.module_slug}")
    print(f"Path: {result.module_path}")
    print(f"Status: {status}")
    print("Checks:")
    for check in result.checks:
        prefix = "OK" if check.passed else "ERR"
        suffix = f" - {check.message}" if check.message else ""
        print(f"- {prefix} {check.name}{suffix}")
    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"- {error}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning}")


def _print_module_plan_text(plan) -> None:
    status = "PASS" if plan.passed else "FAIL"
    print(f"Module: {plan.module_slug}")
    print(f"Display name: {plan.display_name}")
    print(f"Path: {plan.module_path}")
    print(f"Status: {status}")
    print(f"Target exists: {'yes' if plan.target_exists else 'no'}")
    if plan.description:
        print(f"Description: {plan.description}")
    if plan.author:
        print(f"Author: {plan.author}")
    print("Files:")
    for path in plan.files:
        print(f"- {path}")
    if plan.errors:
        print("Errors:")
        for error in plan.errors:
            print(f"- {error}")
    if plan.warnings:
        print("Warnings:")
        for warning in plan.warnings:
            print(f"- {warning}")
    if plan.suggested_next_command:
        print(f"Suggested next command: {plan.suggested_next_command}")


def _join_strings(values) -> str:
    if isinstance(values, (list, tuple)):
        return ", ".join(str(value) for value in values)
    if values in (None, ""):
        return ""
    return str(values)
