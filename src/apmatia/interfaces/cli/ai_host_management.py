from __future__ import annotations

import argparse
import json
import sys


def _api_client():
    from apmatia.interfaces.streamlit import api_client

    return api_client


def add_ai_host_management_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("ai-host-management", help="Manage AI-capable host records.")
    host_subparsers = parser.add_subparsers(dest="ai_host_management_command", required=True)

    list_parser = host_subparsers.add_parser("list", help="List configured AI hosts.")
    list_parser.add_argument("--format", choices=("text", "json"), default="text")
    list_parser.set_defaults(handler=handle_list_hosts)

    add_parser = host_subparsers.add_parser("add", help="Add a new AI host record.")
    _add_host_fields(add_parser)
    add_parser.add_argument("--format", choices=("text", "json"), default="json")
    add_parser.set_defaults(handler=handle_add_host)

    show_parser = host_subparsers.add_parser("show", help="Show an AI host record.")
    show_parser.add_argument("host_id", type=int, help="AI host ID.")
    show_parser.add_argument("--format", choices=("text", "json"), default="json")
    show_parser.set_defaults(handler=handle_show_host)

    update_parser = host_subparsers.add_parser("update", help="Update an AI host record.")
    update_parser.add_argument("host_id", type=int, help="AI host ID.")
    _add_host_fields(update_parser, include_required=False)
    update_parser.add_argument("--format", choices=("text", "json"), default="json")
    update_parser.set_defaults(handler=handle_update_host)

    delete_parser = host_subparsers.add_parser("delete", help="Delete an AI host record.")
    delete_parser.add_argument("host_id", type=int, help="AI host ID.")
    delete_parser.add_argument("--format", choices=("text", "json"), default="json")
    delete_parser.set_defaults(handler=handle_delete_host)

    disable_parser = host_subparsers.add_parser("disable", help="Disable an AI host record.")
    disable_parser.add_argument("host_id", type=int, help="AI host ID.")
    disable_parser.add_argument("--format", choices=("text", "json"), default="json")
    disable_parser.set_defaults(handler=handle_disable_host)

    inspect_parser = host_subparsers.add_parser("inspect", help="Inspect current resource utilization for all AI hosts.")
    inspect_parser.add_argument("--format", choices=("text", "json"), default="json")
    inspect_parser.add_argument("--bootstrap-password", dest="bootstrap_password", default=None, help="SSH password for bootstrapping public key on remote hosts.")
    inspect_parser.set_defaults(handler=handle_inspect_resources)

    test_parser = host_subparsers.add_parser("test", help="Validate a proposed AI host configuration.")
    _add_host_fields(test_parser, include_required=False)
    test_parser.add_argument("--format", choices=("text", "json"), default="json")
    test_parser.set_defaults(handler=handle_test_host)


def _add_host_fields(parser: argparse.ArgumentParser, *, include_required: bool = True) -> None:
    required = {"required": include_required}
    parser.add_argument("--name", default=None, **required)
    parser.add_argument("--hostname", default=None, **required)
    parser.add_argument("--role", default=None, **required)
    parser.add_argument("--connection-type", dest="connection_type", default="local")
    parser.add_argument("--username", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--credential-ref", dest="credential_ref", default=None)
    parser.add_argument("--enabled", dest="enabled", action="store_true")
    parser.add_argument("--disabled", dest="enabled", action="store_false")
    parser.set_defaults(enabled=None)
    parser.add_argument("--notes", default=None)


def handle_list_hosts(args: argparse.Namespace) -> int:
    hosts = _api_client().list_ai_hosts()
    if args.format == "json":
        print(json.dumps(hosts, indent=2))
        return 0
    if not hosts:
        print("No AI hosts found.")
        return 0
    for host in hosts:
        print(
            f"{host.get('id')} | {host.get('name') or ''} | {host.get('hostname') or ''} | "
            f"{host.get('role') or ''} | {host.get('connection_type') or ''} | "
            f"{'enabled' if host.get('enabled', True) else 'disabled'}"
        )
    return 0


def handle_add_host(args: argparse.Namespace) -> int:
    payload = _clean_payload(
        {
            "name": args.name,
            "hostname": args.hostname,
            "role": args.role,
            "connection_type": args.connection_type,
            "username": args.username,
            "port": args.port,
            "credential_ref": args.credential_ref,
            "enabled": args.enabled,
            "notes": args.notes,
        }
    )
    try:
        host = _api_client().create_ai_host(**payload)
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(host, indent=2))
    else:
        print(f"Created AI host {host.get('id')}: {host.get('name')}")
    return 0


def handle_show_host(args: argparse.Namespace) -> int:
    try:
        host = _api_client().show_ai_host(int(args.host_id))
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(host, indent=2))
        return 0
    print(f"Host: {host.get('name') or host.get('id')}")
    print(f"ID: {host.get('id')}")
    print(f"Hostname: {host.get('hostname') or ''}")
    print(f"Role: {host.get('role') or ''}")
    print(f"Connection type: {host.get('connection_type') or ''}")
    print(f"Username: {host.get('username') or ''}")
    print(f"Port: {host.get('port')}")
    print(f"Credential ref: {host.get('credential_ref') or ''}")
    print(f"Enabled: {'yes' if host.get('enabled') else 'no'}")
    print(f"Notes: {host.get('notes') or ''}")
    return 0


def handle_update_host(args: argparse.Namespace) -> int:
    payload = _clean_payload(
        {
            "name": args.name,
            "hostname": args.hostname,
            "role": args.role,
            "connection_type": args.connection_type,
            "username": args.username,
            "port": args.port,
            "credential_ref": args.credential_ref,
            "enabled": args.enabled,
            "notes": args.notes,
        }
    )
    try:
        host = _api_client().update_ai_host(int(args.host_id), **payload)
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    print(json.dumps(host, indent=2))
    return 0


def handle_disable_host(args: argparse.Namespace) -> int:
    try:
        host = _api_client().disable_ai_host(int(args.host_id))
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(host, indent=2))
    else:
        print(f"Disabled AI host {host.get('id')}: {host.get('name')}")
    return 0


def handle_delete_host(args: argparse.Namespace) -> int:
    try:
        result = _api_client().delete_ai_host(int(args.host_id))
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Deleted AI host {result.get('host_id')}")
    return 0

def handle_inspect_resources(args: argparse.Namespace) -> int:
    bootstrap_password = getattr(args, "bootstrap_password", None)
    resources = _api_client().inspect_ai_host_resources(bootstrap_password=bootstrap_password)
    if args.format == "json":
        print(json.dumps(resources, indent=2))
        return 0
    if not resources:
        print("No AI host resources found.")
        return 0
    for resource in resources:
        error = resource.get("resource_error") or ""
        error_suffix = f" | Error: {error}" if error else ""
        print(
            f"{resource.get('host_id')} | {resource.get('name') or ''} | {resource.get('hostname') or ''} | "
            f"{resource.get('resource_status') or ''} | RAM {resource.get('available_ram_bytes', 0)}/{resource.get('total_ram_bytes', 0)} | "
            f"VRAM {resource.get('vram_free_bytes') or 0}/{resource.get('vram_total_bytes') or 0} | "
            f"GPUs {resource.get('detected_gpu_count', 0)}{error_suffix}"
        )
    return 0



def handle_test_host(args: argparse.Namespace) -> int:
    payload = _clean_payload(
        {
            "name": args.name,
            "hostname": args.hostname,
            "role": args.role,
            "connection_type": args.connection_type,
            "username": args.username,
            "port": args.port,
            "credential_ref": args.credential_ref,
            "enabled": args.enabled,
            "notes": args.notes,
        }
    )
    try:
        result = _api_client().validate_ai_host(**payload)
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("Validation passed.")
    return 0


def _clean_payload(payload: dict[str, object | None]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if value is not None}


def _error_message(error: Exception) -> str:
    detail = getattr(error, "detail", None)
    return str(detail if detail not in (None, "") else error)
