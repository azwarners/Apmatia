from __future__ import annotations

import argparse
import getpass
import importlib.metadata
import json
import sys
from pathlib import Path

from . import api_client
from .api_client import CliApiError
from .dynamic import add_dynamic_commands
from .modules import add_module_parser


def build_parser(catalog: list[dict] | None = None) -> argparse.ArgumentParser:
    resolved_catalog = api_client.list_module_commands() if catalog is None else catalog
    parser = argparse.ArgumentParser(
        prog="apmatia",
        description="Apmatia's registry-driven command-line interface.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    subparsers = parser.add_subparsers(dest="command", title="commands")
    add_module_parser(subparsers)
    _add_auth_parsers(subparsers)
    _add_prompt_parser(subparsers)
    commands_parser = subparsers.add_parser("commands", help="List active registry commands.")
    commands_parser.add_argument("--format", choices=("text", "json"), default="text")
    commands_parser.set_defaults(handler=_handle_commands, command_catalog=resolved_catalog)
    add_dynamic_commands(subparsers, resolved_catalog)
    return parser


def _add_auth_parsers(subparsers) -> None:
    login_parser = subparsers.add_parser("login", help="Authenticate the CLI.")
    login_parser.add_argument("username")
    login_parser.add_argument("--password", help="Password; omit to enter it securely.")
    login_parser.set_defaults(handler=_handle_login)

    register_parser = subparsers.add_parser("register", help="Create a user and authenticate the CLI.")
    register_parser.add_argument("username")
    register_parser.add_argument("--password", help="Password; omit to enter it securely.")
    register_parser.set_defaults(handler=_handle_register)

    logout_parser = subparsers.add_parser("logout", help="End the saved CLI session.")
    logout_parser.set_defaults(handler=_handle_logout)

    whoami_parser = subparsers.add_parser("whoami", help="Show the current CLI session.")
    whoami_parser.set_defaults(handler=_handle_whoami)


def _add_prompt_parser(subparsers) -> None:
    parser = subparsers.add_parser("prompt", help="Send a prompt through the Apmatia API.")
    parser.add_argument("text")
    parser.add_argument("--output-dir")
    parser.set_defaults(handler=_handle_prompt)


def _password(args: argparse.Namespace) -> str:
    return str(args.password) if args.password is not None else getpass.getpass("Password: ")


def _handle_login(args: argparse.Namespace) -> int:
    result = api_client.login(args.username, _password(args))
    print(f"Authenticated as {result.get('username') or args.username}.")
    return 0


def _handle_register(args: argparse.Namespace) -> int:
    result = api_client.register(args.username, _password(args))
    user = result.get("user") or {}
    print(f"Registered and authenticated as {user.get('username') or args.username}.")
    return 0


def _handle_logout(_args: argparse.Namespace) -> int:
    api_client.logout()
    print("Logged out.")
    return 0


def _handle_whoami(_args: argparse.Namespace) -> int:
    result = api_client.session()
    if not result.get("authenticated"):
        print("Not authenticated.")
        return 1
    print(f"{result.get('username')} (user {result.get('user_id')})")
    return 0


def _handle_prompt(args: argparse.Namespace) -> int:
    print(api_client.prompt(args.text, output_dir=args.output_dir))
    return 0


def _handle_commands(args: argparse.Namespace) -> int:
    if args.format == "json":
        print(json.dumps(args.command_catalog, indent=2, default=str))
        return 0
    for descriptor in args.command_catalog:
        path = " ".join(str(part).replace("_", "-") for part in descriptor.get("path") or [])
        print(f"{path} - {descriptor.get('description') or descriptor.get('name') or ''}")
    return 0


def _version() -> str:
    try:
        return importlib.metadata.version("apmatia")
    except importlib.metadata.PackageNotFoundError:
        pass
    for path in (Path(__file__).resolve().parents[4] / "VERSION", Path(__file__).resolve().parents[4] / "docs" / "VERSION"):
        if path.exists():
            return path.read_text(encoding="utf-8").strip() or "unknown"
    return "unknown"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        static_commands = {"module", "login", "register", "logout", "whoami", "prompt"}
        parser = build_parser([] if args and (args[0] in static_commands or args[0] == "--version") else None)
    except CliApiError as error:
        print(f"Error loading command catalog: {error.detail}", file=sys.stderr)
        return 1
    if not args:
        parser.print_help()
        return 0
    parsed = parser.parse_args(args)
    handler = getattr(parsed, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    try:
        return int(handler(parsed))
    except (CliApiError, ValueError) as error:
        detail = getattr(error, "detail", str(error))
        print(f"Error: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
