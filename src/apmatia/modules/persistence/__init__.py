"""Shared persistence infrastructure for Apmatia."""

from __future__ import annotations

from .config import load_config_file, save_config_file
from .descriptors import PersistenceDescriptor, RepositoryDescriptor, StoreDescriptor
from .registry import PersistenceRegistry
from .repository import Repository
from .sqlite_store import SQLiteStore
from .store import Store

__all__ = [
    "PersistenceDescriptor",
    "PersistenceRegistry",
    "Repository",
    "RepositoryDescriptor",
    "SQLiteStore",
    "Store",
    "StoreDescriptor",
    "load_config_file",
    "save_config_file",
]
