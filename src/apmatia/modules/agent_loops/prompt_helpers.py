from __future__ import annotations

from typing import Any


def parse_checklist_text(value: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in str(value or "").splitlines():
        text = line.strip()
        if not text:
            continue
        if text[0] in {"-", "*"}:
            text = text[1:].strip()
        items.append({"label": text})
    return items
