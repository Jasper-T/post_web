import os
from pathlib import Path


def _resolve_path_env(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).expanduser().resolve(strict=False)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = _resolve_path_env("FUXING_DATA_ROOT", PROJECT_ROOT / "data")
FILESYSTEM_ROOT = _resolve_path_env("FUXING_FILESYSTEM_ROOT", Path.cwd().anchor or Path("/"))
DATASETS_ROOT = _resolve_path_env("FUXING_DATASETS_ROOT", PROJECT_ROOT / "datasets")
FRONTEND_DIST = _resolve_path_env("FUXING_FRONTEND_DIST", PROJECT_ROOT / "frontend" / "dist")

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
