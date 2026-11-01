"""Convenience entry point when launched from the backend directory."""

import uvicorn

from app.core.config import Settings


if __name__ == "__main__":
    settings = Settings.from_environment()
    uvicorn.run("app.main:app", host="127.0.0.1", port=settings.port, reload=True)
