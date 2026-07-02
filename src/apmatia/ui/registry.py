from __future__ import annotations

from .descriptors import UIDescriptor


class UIRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, UIDescriptor] = {}

    def register(self, descriptor: UIDescriptor) -> None:
        self._descriptors[descriptor.ui_id] = descriptor

    def get(self, ui_id: str) -> UIDescriptor | None:
        return self._descriptors.get(ui_id)

    def list(self) -> list[UIDescriptor]:
        return [self._descriptors[ui_id] for ui_id in sorted(self._descriptors)]
