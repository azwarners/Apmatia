"""Errors shared by the Flet clients."""

from __future__ import annotations


class AdapterError(Exception):
    """Base error for Flet adapters."""


class UnsupportedComponentError(AdapterError):
    """Raised when a component type is not supported."""


class UnsupportedEffectError(AdapterError):
    """Raised when an effect type is not supported."""


class ApiConnectionError(AdapterError):
    """Raised when API connection fails."""


class AuthenticationError(AdapterError):
    """Raised when authentication fails."""
