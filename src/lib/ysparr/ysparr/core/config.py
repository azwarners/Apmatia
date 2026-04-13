from typing import Any, Dict

from src.core.app_config import (
    get_config_value as _get_app_config_value,
    load_app_config,
    save_app_config,
)


def load_config() -> Dict[str, Any]:
    """Load Ysparr configuration from the shared Apmatia config store."""
    return load_app_config()


def save_config(config: Dict[str, Any]) -> None:
    """Persist Ysparr config to the shared Apmatia config store."""
    save_app_config(config)


def get_config_value(*keys, default=None):
    """Retrieve nested config value from the shared Apmatia config store."""
    return _get_app_config_value(*keys, default=default)
