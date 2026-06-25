from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import FRONTEND_DIST


def mount_frontend(app: FastAPI) -> None:
    if FRONTEND_DIST.exists():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def serve_frontend(full_path: str = "") -> FileResponse:
            requested = FRONTEND_DIST / full_path
            if requested.is_file():
                return FileResponse(requested)
            return FileResponse(FRONTEND_DIST / "index.html")

    else:

        @app.get("/", include_in_schema=False)
        def read_root() -> dict[str, str]:
            return {
                "message": "Frontend dist not found. Run the Vue dev server or build the frontend first."
            }
