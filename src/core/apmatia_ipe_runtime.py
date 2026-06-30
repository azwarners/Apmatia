from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from src.modules.apmatia_ipe.services import ApmatiaIpeService

if TYPE_CHECKING:
    from src.modules.apmatia_ipe.sqlite_repositories import SQLiteIpeBundle


APP_DIR = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
DATA_DIR = Path(
    os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
).expanduser()
IPE_DB_PATH = DATA_DIR / "ipe.db"


_bundle: "SQLiteIpeBundle | None" = None
_ipe_service: "ApmatiaIpeService | None" = None


def _ensure_runtime() -> None:
    global _bundle
    global _ipe_service

    if _bundle is None:
        from src.modules.apmatia_ipe.sqlite_repositories import SQLiteIpeBundle

        APP_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteIpeBundle(IPE_DB_PATH)
        _ipe_service = ApmatiaIpeService(_bundle)


def get_ipe_service() -> ApmatiaIpeService:
    _ensure_runtime()
    assert _ipe_service is not None
    return _ipe_service
