"""Descriptor helpers for persistence metadata."""

from __future__ import annotations

from .descriptors import PersistenceDescriptor, RepositoryDescriptor, StoreDescriptor
from .registry import PersistenceRegistry

__all__ = [
    "PersistenceDescriptor",
    "PersistenceRegistry",
    "RepositoryDescriptor",
    "StoreDescriptor",
]
