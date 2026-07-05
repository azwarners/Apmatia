from __future__ import annotations

import argparse
import sys

from apmatia.api.internal.prompt_LLM import prompt_llm

from .ai_host_management import add_ai_host_management_parser
from .ai_model_executor import add_ai_model_executor_parser
from .ai_model_manager import add_ai_model_manager_parser
from .modules import add_module_parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apmatia")
    subparsers = parser.add_subparsers(dest="command")
    add_module_parser(subparsers)
    add_ai_host_management_parser(subparsers)
    add_ai_model_executor_parser(subparsers)
    add_ai_model_manager_parser(subparsers)
    return parser


def _run_legacy_prompt(prompt: str, output_dir: str | None = None) -> int:
    print(prompt_llm(prompt, output_dir=output_dir))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return _run_legacy_prompt("Hello")

    if args[0] not in {"module", "ai-host-management", "ai-model-manager", "ai-model-executor"}:
        prompt = args[0]
        output_dir = args[1] if len(args) > 1 else None
        return _run_legacy_prompt(prompt, output_dir=output_dir)

    parsed = build_parser().parse_args(args)
    handler = getattr(parsed, "handler", None)
    if handler is None:
        return 0
    return int(handler(parsed))


if __name__ == "__main__":
    raise SystemExit(main())
