from __future__ import annotations

from .descriptors import CommandDescriptor


class CommandRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, CommandDescriptor] = {}

    def register(self, descriptor: CommandDescriptor) -> None:
        self._descriptors[descriptor.command_id] = descriptor

    def get(self, command_id: str) -> CommandDescriptor | None:
        return self._descriptors.get(command_id)

    def list(self) -> list[CommandDescriptor]:
        return [self._descriptors[command_id] for command_id in sorted(self._descriptors)]
