from fastapi import APIRouter, Query, Request

from backend.app.schemas.file_upload import FileUploadResponse
from backend.app.services.file_upload import upload_file


router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse)
async def create_uploaded_file(
    request: Request,
    directory: str = Query(...),
    relative_path: str = Query(...),
) -> FileUploadResponse:
    return await upload_file(request, directory=directory, relative_path=relative_path)
