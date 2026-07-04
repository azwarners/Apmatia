from __future__ import annotations

import argparse
import json
import sys


def _api_client():
    from apmatia.interfaces.streamlit import api_client

    return api_client


def add_ai_model_executor_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("ai-model-executor", help="Manage local model execution.")
    executor_subparsers = parser.add_subparsers(dest="ai_model_executor_command", required=True)

    resources_parser = executor_subparsers.add_parser("resources", help="Inspect host RAM and VRAM resources.")
    resources_parser.add_argument("--format", choices=("json", "text"), default="json")
    resources_parser.set_defaults(handler=handle_resources)

    can_run_parser = executor_subparsers.add_parser("can-run", help="Check whether a model can run.")
    can_run_parser.add_argument("model_id", type=int, help="GGUF model ID.")
    can_run_parser.add_argument("--format", choices=("json", "text"), default="json")
    can_run_parser.set_defaults(handler=handle_can_run)

    start_parser = executor_subparsers.add_parser("start", help="Start a model execution.")
    start_parser.add_argument("model_id", type=int, help="GGUF model ID.")
    start_parser.add_argument("--host-id", default="local")
    start_parser.add_argument("--runtime-id", default=None)
    start_parser.add_argument("--port", type=int, default=None)
    start_parser.add_argument("--stop-conflicts", dest="stop_conflicts", action="store_true")
    start_parser.add_argument("--no-stop-conflicts", dest="stop_conflicts", action="store_false")
    start_parser.set_defaults(stop_conflicts=None)
    start_parser.add_argument("--launch-arg", dest="launch_args", action="append", default=[])
    start_parser.add_argument("--format", choices=("json", "text"), default="json")
    start_parser.set_defaults(handler=handle_start)

    stop_parser = executor_subparsers.add_parser("stop", help="Stop a model execution.")
    stop_parser.add_argument("model_id", type=int, help="GGUF model ID.")
    stop_parser.add_argument("--host-id", default="local")
    stop_parser.add_argument("--runtime-id", default=None)
    stop_parser.add_argument("--format", choices=("json", "text"), default="json")
    stop_parser.set_defaults(handler=handle_stop)

    status_parser = executor_subparsers.add_parser("status", help="Show execution status.")
    status_parser.add_argument("--model-id", dest="model_id", type=int, default=None)
    status_parser.add_argument("--format", choices=("json", "text"), default="json")
    status_parser.set_defaults(handler=handle_status)


def handle_resources(args: argparse.Namespace) -> int:
    resources = _api_client().get_ai_model_executor_resources()
    if args.format == "json":
        print(json.dumps(resources, indent=2))
        return 0
    print(f"RAM available: {resources.get('ram_available_bytes', 0)}")
    print(f"VRAM available: {resources.get('vram_available_bytes', 0)}")
    return 0


def handle_can_run(args: argparse.Namespace) -> int:
    try:
        result = _api_client().can_ai_model_run(int(args.model_id))
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(result, indent=2))
        return 0
    print(f"Can run: {result.get('can_run')}")
    for reason in result.get("reasons", []):
        print(f"- {reason}")
    return 0


def handle_start(args: argparse.Namespace) -> int:
    payload = _clean_payload(
        {
            "host_id": args.host_id,
            "runtime_id": args.runtime_id,
            "port": args.port,
            "stop_conflicting_models": args.stop_conflicts,
            "launch_args": args.launch_args,
        }
    )
    try:
        result = _api_client().start_ai_model_execution(int(args.model_id), **payload)
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


def handle_stop(args: argparse.Namespace) -> int:
    payload = _clean_payload({"host_id": args.host_id, "runtime_id": args.runtime_id})
    try:
        result = _api_client().stop_ai_model_execution(int(args.model_id), **payload)
    except Exception as error:
        print(f"Error: {_error_message(error)}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


def handle_status(args: argparse.Namespace) -> int:
    result = _api_client().get_ai_model_execution_status(model_id=args.model_id)
    if args.format == "json":
        print(json.dumps(result, indent=2))
        return 0
    print(f"Executions: {result.get('count', 0)}")
    for item in result.get("items", []):
        print(f"{item.get('id')} | model={item.get('model_id')} | status={item.get('status')} | pid={item.get('pid')}")
    return 0


def _clean_payload(payload: dict[str, object | None]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if value is not None}


def _error_message(error: Exception) -> str:
    detail = getattr(error, "detail", None)
    return str(detail if detail not in (None, "") else error)
