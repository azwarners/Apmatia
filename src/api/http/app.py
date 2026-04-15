import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
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


def _vendor_file_response(asset_path: str) -> FileResponse:
    base = (Path("src/interfaces/web/assets/vendor")).resolve()
    candidate = (base / asset_path).resolve()
    if not str(candidate).startswith(str(base)):
        raise HTTPException(status_code=404, detail="Vendor asset not found")
    if not candidate.is_file() and candidate.suffix == "":
        js_candidate = candidate.with_suffix(".js")
        if js_candidate.is_file():
            candidate = js_candidate
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Vendor asset not found")
    return FileResponse(str(candidate), headers=NO_CACHE_HEADERS)


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


@app.get("/desktop")
def desktop_page(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return _ui_file_response("src/interfaces/web/pages/desktop.html")


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


@app.get("/desktop-shell.js")
def desktop_shell_script():
    return _ui_file_response("src/interfaces/web/js/desktop/desktop-shell.js")


@app.get("/panel-registry.js")
def panel_registry_script():
    return _ui_file_response("src/interfaces/web/js/panel-registry.js")


@app.get("/panel-permissions.js")
def panel_permissions_script():
    return _ui_file_response("src/interfaces/web/js/panel-permissions.js")


@app.get("/layout-manager.js")
def layout_manager_script():
    return _ui_file_response("src/interfaces/web/js/layout-manager.js")


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


@app.get("/apm-discussion-page.js")
def apm_discussion_page_script():
    return _ui_file_response("src/interfaces/web/webcomponents/apm-discussion-page.js")


@app.get("/apm-discussion-tree-page.js")
def apm_discussion_tree_page_script():
    return _ui_file_response("src/interfaces/web/webcomponents/apm-discussion-tree-page.js")


@app.get("/apm-discussion-participants-panel.js")
def apm_discussion_participants_panel_script():
    return _ui_file_response("src/interfaces/web/webcomponents/apm-discussion-participants-panel.js")


@app.get("/apm-discussion-settings-panel.js")
def apm_discussion_settings_panel_script():
    return _ui_file_response("src/interfaces/web/webcomponents/apm-discussion-settings-panel.js")


@app.get("/apm-ai-settings-panel.js")
def apm_ai_settings_panel_script():
    return _ui_file_response("src/interfaces/web/webcomponents/apm-ai-settings-panel.js")


@app.get("/apm-discussion-settings-category-panel.js")
def apm_discussion_settings_category_panel_script():
    return _ui_file_response("src/interfaces/web/webcomponents/apm-discussion-settings-category-panel.js")


@app.get("/apm-theme-settings-panel.js")
def apm_theme_settings_panel_script():
    return _ui_file_response("src/interfaces/web/webcomponents/apm-theme-settings-panel.js")


@app.get("/apm-about-panel.js")
def apm_about_panel_script():
    return _ui_file_response("src/interfaces/web/webcomponents/apm-about-panel.js")


@app.get("/vendor/golden-layout/golden-layout.min.js")
def vendor_golden_layout_js():
    return _ui_file_response("src/interfaces/web/assets/vendor/golden-layout/golden-layout.min.js")


@app.get("/vendor/golden-layout/goldenlayout-base.min.css")
def vendor_golden_layout_base_css():
    return _ui_file_response("src/interfaces/web/assets/vendor/golden-layout/goldenlayout-base.min.css")


@app.get("/vendor/golden-layout/goldenlayout-dark-theme.min.css")
def vendor_golden_layout_dark_css():
    return _ui_file_response("src/interfaces/web/assets/vendor/golden-layout/goldenlayout-dark-theme.min.css")


@app.get("/vendor/golden-layout/goldenlayout-light-theme.min.css")
def vendor_golden_layout_light_css():
    return _ui_file_response("src/interfaces/web/assets/vendor/golden-layout/goldenlayout-light-theme.min.css")


@app.get("/vendor/golden-layout/{asset_path:path}")
def vendor_golden_layout_asset(asset_path: str):
    return _vendor_file_response(f"golden-layout/{asset_path}")
