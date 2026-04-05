import json
from pathlib import Path
from typing import Any, Dict


CONFIG_DIR = Path.home() / ".ysparr"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> Dict[str, Any]:
    """
    Load Ysparr configuration from ~/.ysparr/config.json

    Returns empty dict if file does not exist.
    """

    if not CONFIG_FILE.exists():
        return {}

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_config_value(*keys, default=None):
    """
    Retrieve nested config value.

    Example:
        get_config_value("text2text", "koboldcpp", "base_url")
    """

    config = load_config()

    current = config
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)

    return current if current is not None else default
