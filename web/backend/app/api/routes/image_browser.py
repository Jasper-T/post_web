from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from backend.app.schemas.image_browser import ImageBrowseResponse
from backend.app.services.image_browser import browse_images, serve_image


router = APIRouter(prefix="/images", tags=["images"])


@router.get("/browse", response_model=ImageBrowseResponse)
def read_image_browser(
    path: str = Query(..., description="Absolute filesystem path to a directory or image file"),
) -> ImageBrowseResponse:
    return ImageBrowseResponse(**browse_images(path))


@router.get("/content")
def read_image_content(
    path: str = Query(..., description="Absolute image path"),
) -> FileResponse:
    return serve_image(path)
