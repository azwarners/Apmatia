from __future__ import annotations

from typing import TYPE_CHECKING

from apmatia.core.runtime_paths import get_app_dir, get_data_dir
from apmatia.modules.apmatia_ipe.services import ApmatiaIpeService

if TYPE_CHECKING:
    from apmatia.modules.apmatia_ipe.sqlite_repositories import SQLiteIpeBundle


APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
IPE_DB_PATH = DATA_DIR / "ipe.db"
_DEFAULT_APP_DIR = APP_DIR
_DEFAULT_DATA_DIR = DATA_DIR
_DEFAULT_IPE_DB_PATH = IPE_DB_PATH


_bundle: "SQLiteIpeBundle | None" = None
_ipe_service: "ApmatiaIpeService | None" = None


def _ensure_runtime() -> None:
    global _bundle
    global _ipe_service

    if _bundle is None:
        from apmatia.modules.apmatia_ipe.sqlite_repositories import SQLiteIpeBundle

        app_dir = APP_DIR if APP_DIR != _DEFAULT_APP_DIR else get_app_dir()
        data_dir = DATA_DIR if DATA_DIR != _DEFAULT_DATA_DIR else get_data_dir()
        db_path = IPE_DB_PATH if IPE_DB_PATH != _DEFAULT_IPE_DB_PATH else data_dir / "ipe.db"
        app_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteIpeBundle(db_path)
        _ipe_service = ApmatiaIpeService(_bundle)


def get_ipe_service() -> ApmatiaIpeService:
    _ensure_runtime()
    assert _ipe_service is not None
    return _ipe_service
