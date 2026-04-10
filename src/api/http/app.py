from fastapi import FastAPI
from src.api.http.routes import router
from fastapi.responses import FileResponse

def create_app():
    app = FastAPI(title="python_core_api_ui_template")
    app.include_router(router, prefix="/api")
    return app

app = create_app()

@app.get("/")
def root():
    return FileResponse("src/interfaces/web/desktop/index.html")


@app.get("/discussion")
def discussion_page():
    return FileResponse("src/interfaces/web/desktop/discussion.html")


@app.get("/settings")
def settings_page():
    return FileResponse("src/interfaces/web/desktop/settings.html")


@app.get("/styles.css")
def styles():
    return FileResponse("src/interfaces/web/desktop/styles.css")


@app.get("/discussion.js")
def discussion_script():
    return FileResponse("src/interfaces/web/desktop/discussion.js")


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
