"""Descriptor helpers for command metadata."""

from __future__ import annotations

from .descriptors import CommandDescriptor
from .registry import CommandRegistry
from .runner import run_command

__all__ = ["CommandDescriptor", "CommandRegistry", "run_command"]
