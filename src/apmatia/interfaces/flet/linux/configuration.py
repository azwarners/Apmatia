"""Configuration for the Apmatia Linux Client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


DEFAULT_CORE_URL = "http://127.0.0.1:8000/api"


def normalize_core_url(value: str | None) -> str:
    """Return a normalized Apmatia API base URL."""
    raw_value = (value or DEFAULT_CORE_URL).strip() or DEFAULT_CORE_URL
    parts = urlsplit(raw_value.rstrip("/"))
    path = parts.path.rstrip("/")
    if not path or path == "/":
        path = "/api"
    elif not path.endswith("/api"):
        path = f"{path}/api"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment)).rstrip("/")


@dataclass(frozen=True)
class ClientConfiguration:
    """Runtime settings for the Linux client."""

    core_url: str = DEFAULT_CORE_URL
    window_width: float = 1100
    window_height: float = 700
    minimum_window_width: float = 800
    minimum_window_height: float = 500

    @classmethod
    def from_environment(cls) -> "ClientConfiguration":
        """Load client configuration from the process environment."""
        def number(name: str, default: float) -> float:
            try:
                return float(os.environ.get(name, default))
            except (TypeError, ValueError):
                return default

        return cls(
            core_url=normalize_core_url(os.environ.get("APMATIA_API_URL")),
            window_width=number("APMATIA_FLET_WINDOW_WIDTH", cls.window_width),
            window_height=number("APMATIA_FLET_WINDOW_HEIGHT", cls.window_height),
            minimum_window_width=number("APMATIA_FLET_MIN_WINDOW_WIDTH", cls.minimum_window_width),
            minimum_window_height=number("APMATIA_FLET_MIN_WINDOW_HEIGHT", cls.minimum_window_height),
        )
