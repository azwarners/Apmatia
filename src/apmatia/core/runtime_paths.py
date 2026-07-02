from __future__ import annotations

import os
from pathlib import Path


def get_app_dir() -> Path:
    return Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()


def get_data_dir() -> Path:
    return Path(
        os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
    ).expanduser()
