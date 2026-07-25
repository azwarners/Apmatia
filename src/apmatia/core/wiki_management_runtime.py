from __future__ import annotations

from typing import TYPE_CHECKING

from apmatia.modules.knowledge_wiki.manager import WikiManager
from apmatia.core.runtime_paths import get_app_dir, get_data_dir

if TYPE_CHECKING:
    from apmatia.modules.knowledge_wiki.sqlite_repositories import SQLiteWikiManagementBundle


APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
WIKI_DB_PATH = DATA_DIR / "wikis.db"
_DEFAULT_APP_DIR = APP_DIR
_DEFAULT_DATA_DIR = DATA_DIR
_DEFAULT_WIKI_DB_PATH = WIKI_DB_PATH


_bundle: "SQLiteWikiManagementBundle | None" = None
_wiki_manager: "WikiManager | None" = None


def _ensure_runtime() -> None:
    global _bundle
    global _wiki_manager

    if _bundle is None:
        from apmatia.modules.knowledge_wiki.sqlite_repositories import SQLiteWikiManagementBundle

        app_dir = APP_DIR if APP_DIR != _DEFAULT_APP_DIR else get_app_dir()
        data_dir = DATA_DIR if DATA_DIR != _DEFAULT_DATA_DIR else get_data_dir()
        db_path = WIKI_DB_PATH if WIKI_DB_PATH != _DEFAULT_WIKI_DB_PATH else data_dir / "wikis.db"
        app_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        _bundle = SQLiteWikiManagementBundle(db_path)
        _wiki_manager = WikiManager(_bundle.wikis, _bundle.nodes)


def get_wiki_manager() -> WikiManager:
    _ensure_runtime()
    assert _wiki_manager is not None
    return _wiki_manager
