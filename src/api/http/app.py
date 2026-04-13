import os
from pathlib import Path

from fastapi import FastAPI, Request
from src.api.http.routes import router
from fastapi.responses import FileResponse, RedirectResponse
from src.api.internal.auth import get_session

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _ensure_runtime_dirs() -> None:
    app_dir = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
    data_dir = Path(
        os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
    ).expanduser()
    app_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)


def _read_version() -> str:
    version_path = Path(__file__).resolve().parents[3] / "VERSION"
    if not version_path.exists():
        return "unknown"
    return version_path.read_text(encoding="utf-8").strip() or "unknown"


def create_app():
    _ensure_runtime_dirs()
    app = FastAPI(title="python_core_api_ui_template")
    app.include_router(router, prefix="/api")
    return app

app = create_app()


def _is_authenticated(request: Request) -> bool:
    token = request.cookies.get("apmatia_session")
    return get_session(token) is not None


def _ui_file_response(path: str) -> FileResponse:
    return FileResponse(path, headers=NO_CACHE_HEADERS)


@app.get("/api/version")
def api_version() -> dict:
    return {"version": _read_version()}


@app.get("/")
def root(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return _ui_file_response("src/interfaces/web/index.html")


@app.get("/discussion")
def discussion_page(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return _ui_file_response("src/interfaces/web/pages/discussion.html")


@app.get("/discussion_tree")
def discussion_tree_page(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return _ui_file_response("src/interfaces/web/pages/discussion_tree.html")


@app.get("/settings")
def settings_page(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return _ui_file_response("src/interfaces/web/pages/settings.html")


@app.get("/login")
def login_page():
    return _ui_file_response("src/interfaces/web/pages/login.html")


@app.get("/styles.css")
def styles():
    return _ui_file_response("src/interfaces/web/styles.css")


@app.get("/discussion.js")
def discussion_script():
    return _ui_file_response("src/interfaces/web/js/discussion/discussion.js")


@app.get("/discussion-tree.js")
def discussion_tree_script():
    return _ui_file_response("src/interfaces/web/js/discussion/discussion-tree.js")


@app.get("/settings.js")
def settings_script():
    return _ui_file_response("src/interfaces/web/js/settings/settings.js")


@app.get("/ai-settings.js")
def ai_settings_script():
    return _ui_file_response("src/interfaces/web/webcomponents/ai-settings.js")


@app.get("/discussion-settings.js")
def discussion_settings_script():
    return _ui_file_response("src/interfaces/web/webcomponents/discussion-settings.js")


@app.get("/theme-settings.js")
def theme_settings_script():
    return _ui_file_response("src/interfaces/web/webcomponents/theme-settings.js")


@app.get("/theme-runtime.js")
def theme_runtime_script():
    return _ui_file_response("src/interfaces/web/js/settings/theme-runtime.js")


@app.get("/about-info.js")
def about_info_script():
    return _ui_file_response("src/interfaces/web/webcomponents/about-info.js")


@app.get("/login.js")
def login_script():
    return _ui_file_response("src/interfaces/web/js/users/login.js")


@app.get("/auth-ui.js")
def auth_ui_script():
    return _ui_file_response("src/interfaces/web/js/users/auth-ui.js")


@app.get("/mobile-menu.js")
def mobile_menu_script():
    return _ui_file_response("src/interfaces/web/mobile-menu.js")


@app.get("/mobile-drawer.js")
def mobile_drawer_script():
    return _ui_file_response("src/interfaces/web/webcomponents/mobile-drawer.js")


@app.get("/folder-browser.js")
def folder_browser_script():
    return _ui_file_response("src/interfaces/web/webcomponents/folder-browser.js")


@app.get("/folder-picker.js")
def folder_picker_script():
    return _ui_file_response("src/interfaces/web/webcomponents/folder-picker.js")


@app.get("/tree-list-item.js")
def tree_list_item_script():
    return _ui_file_response("src/interfaces/web/webcomponents/tree-list-item.js")


@app.get("/tree-list.js")
def tree_list_script():
    return _ui_file_response("src/interfaces/web/webcomponents/tree-list.js")


@app.get("/discussion-tree-list-items.js")
def discussion_tree_list_items_script():
    return _ui_file_response("src/interfaces/web/webcomponents/discussion-tree-list-items.js")


@app.get("/discussion-tree-component.js")
def discussion_tree_component_script():
    return _ui_file_response("src/interfaces/web/webcomponents/discussion-tree-component.js")
