import os
import uvicorn
from src.api.http.app import app

if __name__ == "__main__":
    # Get host from environment variable, default to 0.0.0.0 for LAN access
    host = os.environ.get("APMATIA_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=8000)
