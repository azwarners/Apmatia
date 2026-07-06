from __future__ import annotations

import importlib
import pkgutil
from functools import lru_cache

from .registry import Registry

_LEGACY_BUNDLED_MODULE_DIRS = set()


def load_bundled_modules(registry: Registry) -> Registry:
    package = importlib.import_module("apmatia.modules")
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name.startswith("_"):
            continue
        if module_info.name in _LEGACY_BUNDLED_MODULE_DIRS:
            continue
        module = importlib.import_module(f"{package.__name__}.{module_info.name}.module")
        register = getattr(module, "register", None)
        if callable(register):
            register(registry)
    return registry


def create_application_registry() -> Registry:
    registry = Registry()
    return load_bundled_modules(registry)


@lru_cache(maxsize=1)
def get_application_registry() -> Registry:
    return create_application_registry()
