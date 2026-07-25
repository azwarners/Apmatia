from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from threading import RLock

from apmatia.core.app_config import get_config_value

from .registry import Registry

_LEGACY_BUNDLED_MODULE_DIRS = set()
_active_module_names: set[str] = set()
_application_registry: Registry | None = None
_application_registry_mode: bool | None = None
_registry_lock = RLock()


def load_bundled_modules(registry: Registry, *, include_development: bool | None = None) -> Registry:
    from apmatia.core.modules.manifest import load_module_manifest

    development_enabled = _development_modules_enabled() if include_development is None else bool(include_development)
    package = importlib.import_module("apmatia.modules")
    package_dir = Path(package.__path__[0])
    loaded_module_names: set[str] = set()
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name.startswith("_"):
            continue
        if module_info.name in _LEGACY_BUNDLED_MODULE_DIRS:
            continue
        module_dir = package_dir / module_info.name
        manifest_path = module_dir / "manifest.toml"
        if not manifest_path.exists():
            continue
        manifest = load_module_manifest(module_dir)
        if not development_enabled and not (manifest.is_stable and manifest.default_enabled):
            continue
        module = importlib.import_module(f"{package.__name__}.{module_info.name}.module")
        register = getattr(module, "register", None)
        if callable(register):
            register(registry)
            loaded_module_names.add(module_info.name)
    _active_module_names.clear()
    _active_module_names.update(loaded_module_names)
    return registry


def create_application_registry(*, include_development: bool | None = None) -> Registry:
    registry = Registry()
    return load_bundled_modules(registry, include_development=include_development)


def get_application_registry() -> Registry:
    development_enabled = _development_modules_enabled()
    with _registry_lock:
        if _application_registry is None or _application_registry_mode != development_enabled:
            _replace_application_registry(development_enabled)
        if _application_registry is None:
            raise RuntimeError("Application registry failed to initialize.")
        return _application_registry


def refresh_application_registry() -> Registry:
    with _registry_lock:
        _replace_application_registry(_development_modules_enabled())
        if _application_registry is None:
            raise RuntimeError("Application registry failed to initialize.")
        return _application_registry


def clear_application_registry() -> None:
    global _application_registry
    global _application_registry_mode

    with _registry_lock:
        _deactivate_loaded_modules()
        from apmatia.core.module_view_runtime import clear_module_view_providers

        clear_module_view_providers()
        _application_registry = None
        _application_registry_mode = None


def _replace_application_registry(development_enabled: bool) -> None:
    global _application_registry
    global _application_registry_mode

    _deactivate_loaded_modules()
    from apmatia.core.module_view_runtime import clear_module_view_providers

    clear_module_view_providers()
    _application_registry = create_application_registry(include_development=development_enabled)
    _application_registry_mode = development_enabled


def _development_modules_enabled() -> bool:
    return bool(get_config_value("ui", "show_development_modules", default=False))


def _deactivate_loaded_modules() -> None:
    for module_name in sorted(_active_module_names):
        module = importlib.import_module(f"apmatia.modules.{module_name}.module")
        deactivate = getattr(module, "deactivate", None)
        if callable(deactivate):
            deactivate()
    _active_module_names.clear()


get_application_registry.cache_clear = clear_application_registry  # type: ignore[attr-defined]
