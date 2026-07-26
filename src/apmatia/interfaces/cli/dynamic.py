from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from typing import Any

from . import api_client


def add_dynamic_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    catalog: list[dict[str, Any]],
) -> None:
    modules: dict[str, list[dict[str, Any]]] = {}
    for descriptor in catalog:
        path = _command_path(descriptor)
        if len(path) < 2:
            continue
        modules.setdefault(path[0], []).append(descriptor)

    for module_id, commands in sorted(modules.items()):
        first = commands[0]
        module_parser = subparsers.add_parser(
            _cli_name(module_id),
            help=str(first.get("module_description") or first.get("module_name") or "Module commands."),
            description=str(first.get("module_description") or ""),
        )
        module_subparsers = module_parser.add_subparsers(dest=f"dynamic_{module_id}", required=True)
        _add_level(module_subparsers, commands, depth=1)


def _add_level(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    commands: list[dict[str, Any]],
    *,
    depth: int,
) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for descriptor in commands:
        path = _command_path(descriptor)
        if depth < len(path):
            grouped.setdefault(path[depth], []).append(descriptor)

    for segment, entries in sorted(grouped.items()):
        leaf = next((entry for entry in entries if len(_command_path(entry)) == depth + 1), None)
        children = [entry for entry in entries if len(_command_path(entry)) > depth + 1]
        description = str((leaf or entries[0]).get("description") or (leaf or entries[0]).get("name") or "")
        parser = subparsers.add_parser(_cli_name(segment), help=description, description=description)
        if leaf is not None:
            _configure_command_parser(parser, leaf)
        if children:
            child_subparsers = parser.add_subparsers(dest=f"dynamic_level_{depth}", required=leaf is None)
            _add_level(child_subparsers, children, depth=depth + 1)


def _configure_command_parser(parser: argparse.ArgumentParser, descriptor: dict[str, Any]) -> None:
    parser.set_defaults(handler=handle_dynamic_command, dynamic_descriptor=descriptor)
    for field in descriptor.get("fields") or []:
        if isinstance(field, Mapping):
            _add_field_argument(parser, field)
    parser.add_argument("--payload", help="JSON object merged with generated command arguments.")
    parser.add_argument("--format", choices=("json", "text"), default="json", help="Result output format.")


def _add_field_argument(parser: argparse.ArgumentParser, field: Mapping[str, Any]) -> None:
    key = str(field.get("key") or "").strip()
    if not key:
        return
    option = f"--{_cli_name(key)}"
    kwargs: dict[str, Any] = {
        "dest": f"dynamic_field_{key}",
        "default": argparse.SUPPRESS,
        "required": bool(field.get("required", False)),
        "help": str(field.get("help_text") or field.get("label") or ""),
        "metavar": key.upper(),
    }
    options = field.get("options")
    if isinstance(options, (list, tuple)) and options:
        kwargs["choices"] = [str(option) for option in options]
    data_type = str(field.get("data_type") or "").lower()
    field_type = str(field.get("field_type") or "").lower()
    if data_type == "boolean" or field_type in {"checkbox", "toggle", "boolean"}:
        kwargs.pop("metavar", None)
        kwargs["action"] = argparse.BooleanOptionalAction
    elif data_type == "number" or field_type == "number":
        numeric_values = (field.get("default"), field.get("min_value"), field.get("max_value"), field.get("step"))
        kwargs["type"] = float if any(isinstance(value, float) for value in numeric_values) else int
    elif data_type in {"list", "string_list"}:
        kwargs["action"] = "append"
    parser.add_argument(option, **kwargs)


def handle_dynamic_command(args: argparse.Namespace) -> int:
    descriptor = dict(args.dynamic_descriptor)
    payload: dict[str, Any] = {}
    if args.payload:
        try:
            decoded = json.loads(args.payload)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid --payload JSON: {error.msg}") from error
        if not isinstance(decoded, dict):
            raise ValueError("--payload must contain a JSON object.")
        payload.update(decoded)
    for key, value in vars(args).items():
        if key.startswith("dynamic_field_"):
            payload[key.removeprefix("dynamic_field_")] = value
    result = api_client.execute_module_command(str(descriptor["command_id"]), payload)
    _print_result(result, output_format=args.format)
    return 0


def _print_result(result: Any, *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result, indent=2, default=str))
        return
    if isinstance(result, Mapping):
        for key, value in result.items():
            if isinstance(value, (dict, list)):
                print(f"{key}: {json.dumps(value, default=str)}")
            else:
                print(f"{key}: {value}")
        return
    print(result)


def _command_path(descriptor: Mapping[str, Any]) -> list[str]:
    raw = descriptor.get("path")
    if isinstance(raw, list) and raw:
        return [str(part) for part in raw]
    return str(descriptor.get("command_id") or "").split(".")


def _cli_name(value: str) -> str:
    return value.replace("_", "-")
