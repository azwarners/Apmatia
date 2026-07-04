from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _api_client():
    from apmatia.interfaces.streamlit import api_client

    return api_client


class ApiError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def add_ai_model_manager_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("ai-model-manager", help="Manage local GGUF model metadata.")
    model_subparsers = parser.add_subparsers(dest="ai_model_manager_command", required=True)

    list_parser = model_subparsers.add_parser("list", help="List GGUF models.")
    list_parser.add_argument("--format", choices=("text", "json"), default="text")
    list_parser.set_defaults(handler=handle_list_models)

    scan_parser = model_subparsers.add_parser("scan", help="Scan a directory for GGUF models.")
    scan_parser.add_argument("directory", help="Directory to scan.")
    recursive_group = scan_parser.add_mutually_exclusive_group()
    recursive_group.add_argument("--recursive", dest="recursive", action="store_true", help="Scan nested directories.")
    recursive_group.add_argument("--shallow", dest="recursive", action="store_false", help="Only scan the top-level directory.")
    scan_parser.set_defaults(recursive=True)
    scan_parser.add_argument("--format", choices=("text", "json"), default="text")
    scan_parser.set_defaults(handler=handle_scan_models)

    show_parser = model_subparsers.add_parser("show", help="Show GGUF model details.")
    show_parser.add_argument("model_id", type=int, help="GGUF model ID.")
    show_parser.add_argument("--format", choices=("text", "json"), default="text")
    show_parser.set_defaults(handler=handle_show_model)

    update_parser = model_subparsers.add_parser("update", help="Update a GGUF model record.")
    update_parser.add_argument("model_id", type=int, help="GGUF model ID.")
    update_parser.add_argument("--name", default=None)
    update_parser.add_argument("--local-path", dest="local_path", default=None)
    update_parser.add_argument("--file-size-bytes", dest="file_size_bytes", type=int, default=None)
    update_parser.add_argument("--size-class", dest="size_class", default=None)
    update_parser.add_argument("--cost-mode", dest="cost_mode", default=None)
    update_parser.add_argument("--input-token-cost-per-1k", dest="input_token_cost_per_1k", type=float, default=None)
    update_parser.add_argument("--output-token-cost-per-1k", dest="output_token_cost_per_1k", type=float, default=None)
    update_parser.add_argument("--notes", default=None)
    update_parser.set_defaults(handler=handle_update_model)

    preference_parser = model_subparsers.add_parser("preferences", help="Manage task preferences.")
    preference_subparsers = preference_parser.add_subparsers(dest="preference_command", required=True)

    pref_list_parser = preference_subparsers.add_parser("list", help="List task preferences.")
    pref_list_parser.add_argument("--format", choices=("text", "json"), default="text")
    pref_list_parser.set_defaults(handler=handle_list_preferences)

    pref_update_parser = preference_subparsers.add_parser("update", help="Update a task preference.")
    pref_update_parser.add_argument("preference_id", type=int, help="Task preference ID.")
    pref_update_parser.add_argument("--task-name", dest="task_name", default=None)
    pref_update_parser.add_argument("--preferred-size-classes", dest="preferred_size_classes", default=None)
    pref_update_parser.add_argument("--notes", default=None)
    pref_update_parser.set_defaults(handler=handle_update_preference)


def handle_list_models(args: argparse.Namespace) -> int:
    models = _api_client().list_ai_models()
    if args.format == "json":
        print(json.dumps(models, indent=2))
        return 0
    if not models:
        print("No GGUF models found.")
        return 0
    for model in models:
        print(
            f"{model.get('id')} | {model.get('name') or ''} | {model.get('size_class') or ''} | "
            f"{'vision' if model.get('vision_enabled') else 'text'} | {model.get('cost_mode') or 'free'} | "
            f"{model.get('file_size_human') or _humanize_bytes(model.get('file_size_bytes'))}"
        )
    return 0


def handle_scan_models(args: argparse.Namespace) -> int:
    try:
        result = _api_client().scan_ai_models(args.directory, recursive=bool(args.recursive))
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Scanned {result.get('scanned', 0)} files.")
        print(f"Created: {result.get('created', 0)}")
        print(f"Updated: {result.get('updated', 0)}")
    return 0


def handle_show_model(args: argparse.Namespace) -> int:
    try:
        model = _api_client().show_ai_model(int(args.model_id))
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(model, indent=2))
        return 0
    print(f"Model: {model.get('name') or model.get('id')}")
    print(f"ID: {model.get('id')}")
    print(f"Path: {model.get('local_path') or ''}")
    print(f"File size: {model.get('file_size_human') or _humanize_bytes(model.get('file_size_bytes'))}")
    print(f"Size class: {model.get('size_class') or ''}")
    print(f"Vision enabled: {'yes' if model.get('vision_enabled') else 'no'}")
    print(f"Cost mode: {model.get('cost_mode') or 'free'}")
    print(f"Input token cost / 1k: {model.get('input_token_cost_per_1k')}")
    print(f"Output token cost / 1k: {model.get('output_token_cost_per_1k')}")
    return 0


def handle_update_model(args: argparse.Namespace) -> int:
    payload = _clean_payload(
        {
            "name": args.name,
            "local_path": args.local_path,
            "file_size_bytes": args.file_size_bytes,
            "size_class": args.size_class,
            "cost_mode": args.cost_mode,
            "input_token_cost_per_1k": args.input_token_cost_per_1k,
            "output_token_cost_per_1k": args.output_token_cost_per_1k,
            "notes": args.notes,
        }
    )
    try:
        model = _api_client().update_ai_model(int(args.model_id), **payload)
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    print(json.dumps(model, indent=2))
    return 0


def handle_list_preferences(args: argparse.Namespace) -> int:
    preferences = _api_client().list_ai_model_preferences()
    if args.format == "json":
        print(json.dumps(preferences, indent=2))
        return 0
    if not preferences:
        print("No task preferences found.")
        return 0
    for item in preferences:
        print(
            f"{item.get('id')} | {item.get('task_name') or ''} | "
            f"{_join_values(item.get('preferred_size_classes'))}"
        )
    return 0


def handle_update_preference(args: argparse.Namespace) -> int:
    payload = _clean_payload(
        {
            "task_name": args.task_name,
            "preferred_size_classes": args.preferred_size_classes,
            "notes": args.notes,
        }
    )
    try:
        preference = _api_client().update_ai_model_preference(int(args.preference_id), **payload)
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    print(json.dumps(preference, indent=2))
    return 0


def _clean_payload(payload: dict[str, object | None]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if value is not None}


def _join_values(values: object) -> str:
    if isinstance(values, (list, tuple)):
        return ", ".join(str(item) for item in values)
    return "" if values in (None, "") else str(values)


def _error_message(error: Exception) -> str:
    detail = getattr(error, "detail", None)
    return str(detail if detail not in (None, "") else error)


def _humanize_bytes(value: object) -> str:
    try:
        size = float(int(value or 0))
    except (TypeError, ValueError):
        size = 0.0
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    for unit in units:
        if size < 1000.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1000.0
