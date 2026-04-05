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

