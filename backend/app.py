"""FastAPI application factory.

Run with the factory flag so no database file is created at import time:

    uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import Settings
from .db import Database
from .routers import auth, conversations, devices

_MISSING_FRONTEND = """<!doctype html><meta charset="utf-8"><title>CLAD</title>
<body style="font-family:system-ui;padding:2rem">
<h1>CLAD 后端已启动</h1>
<p>未找到前端目录。请设置 CLAD_FRONTEND_DIR 指向 frontend/ 后重启。</p>
</body>"""


def create_app(settings: Settings | None = None, init_db: bool = True) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings.database_url)
    if init_db:
        database.create_all()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        database.dispose()

    app = FastAPI(title="CLAD", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.db = database

    app.include_router(auth.router, prefix="/api")
    app.include_router(devices.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")

    @app.get("/api/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    # The frontend is a separate worktree/directory configured at startup
    # (CLAD_FRONTEND_DIR). When it is absent the API still works and / returns a
    # clear message instead of the process failing to boot.
    if settings.frontend_dir.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=str(settings.frontend_dir)),
            name="static",
        )
    else:

        @app.get("/static/{asset_path:path}", include_in_schema=False)
        def static_unavailable(asset_path: str) -> Response:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="前端文件未配置")

    @app.get("/", include_in_schema=False)
    def index() -> Response:
        index_file = settings.frontend_dir / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return HTMLResponse(_MISSING_FRONTEND, status_code=503)

    return app
