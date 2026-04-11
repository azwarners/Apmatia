import os
from pathlib import Path

from fastapi import FastAPI, Request
from src.api.http.routes import router
from fastapi.responses import FileResponse, RedirectResponse
from src.api.internal.auth import get_session


def _ensure_runtime_dirs() -> None:
    app_dir = Path(os.getenv("APMATIA_HOME", str(Path.home() / ".apmatia"))).expanduser()
    data_dir = Path(
        os.getenv("APMATIA_DATA_DIR", str(Path.home() / ".local" / "share" / "apmatia"))
    ).expanduser()
    app_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)


def create_app():
    _ensure_runtime_dirs()
    app = FastAPI(title="python_core_api_ui_template")
    app.include_router(router, prefix="/api")
    return app

app = create_app()


def _is_authenticated(request: Request) -> bool:
    token = request.cookies.get("apmatia_session")
    return get_session(token) is not None


@app.get("/")
def root(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return FileResponse("src/interfaces/web/desktop/index.html")


@app.get("/discussion")
def discussion_page(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return FileResponse("src/interfaces/web/desktop/discussion.html")


@app.get("/discussion_tree")
def discussion_tree_page(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return FileResponse("src/interfaces/web/desktop/discussion_tree.html")


@app.get("/settings")
def settings_page(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return FileResponse("src/interfaces/web/desktop/settings.html")


@app.get("/login")
def login_page():
    return FileResponse("src/interfaces/web/desktop/login.html")


@app.get("/styles.css")
def styles():
    return FileResponse("src/interfaces/web/desktop/styles.css")


@app.get("/discussion.js")
def discussion_script():
    return FileResponse("src/interfaces/web/desktop/discussion.js")


@app.get("/discussion-tree.js")
def discussion_tree_script():
    return FileResponse("src/interfaces/web/desktop/discussion-tree.js")


@app.get("/settings.js")
def settings_script():
    return FileResponse("src/interfaces/web/desktop/settings.js")


@app.get("/ai-settings.js")
def ai_settings_script():
    return FileResponse("src/interfaces/web/desktop/ai-settings.js")


@app.get("/discussion-settings.js")
def discussion_settings_script():
    return FileResponse("src/interfaces/web/desktop/discussion-settings.js")


@app.get("/theme-settings.js")
def theme_settings_script():
    return FileResponse("src/interfaces/web/desktop/theme-settings.js")


@app.get("/theme-runtime.js")
def theme_runtime_script():
    return FileResponse("src/interfaces/web/desktop/theme-runtime.js")


@app.get("/login.js")
def login_script():
    return FileResponse("src/interfaces/web/desktop/login.js")


@app.get("/auth-ui.js")
def auth_ui_script():
    return FileResponse("src/interfaces/web/desktop/auth-ui.js")


@app.get("/mobile-menu.js")
def mobile_menu_script():
    return FileResponse("src/interfaces/web/desktop/mobile-menu.js")
