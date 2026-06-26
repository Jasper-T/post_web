from fastapi import APIRouter

from backend.app.core.config import DATASETS_ROOT, FILESYSTEM_ROOT, FRONTEND_DIST


router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def read_config() -> dict[str, str]:
    return {
        "filesystemRoot": str(FILESYSTEM_ROOT),
        "datasetsRoot": str(DATASETS_ROOT),
        "frontendDist": str(FRONTEND_DIST),
    }
