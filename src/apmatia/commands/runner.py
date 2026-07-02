from __future__ import annotations

from collections.abc import Callable
from typing import Any


def run_command(command: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
    return command(*args, **kwargs)
