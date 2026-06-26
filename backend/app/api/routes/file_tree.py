from fastapi import APIRouter, Query

from backend.app.core.config import FILESYSTEM_ROOT
from backend.app.schemas.file_tree import TreeResponse
from backend.app.services.file_tree import read_directory_tree


router = APIRouter()


@router.get("/tree", response_model=TreeResponse)
def read_tree(
    path: str = Query(default=str(FILESYSTEM_ROOT), description="Absolute filesystem path"),
    offset: int = Query(default=0, ge=0, description="Number of directory entries to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum directory entries to return"),
    filter: str | None = Query(default=None, description="Case-sensitive name filter"),
) -> TreeResponse:
    return read_directory_tree(path, offset=offset, limit=limit, filter_text=filter)
