from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from natsort import natsorted

from backend.app.services.file_tree import resolve_filesystem_path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def _list_directory_images(directory: Path) -> list[Path]:
    try:
        images = [child for child in directory.iterdir() if is_image_file(child)]
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Permission denied") from exc

    return natsorted(images, key=lambda item: item.name)


def browse_images(raw_path: str) -> dict:
    target = resolve_filesystem_path(raw_path)

    if target.is_dir():
        directory = target
        selected_path = None
        images = _list_directory_images(directory)
    elif is_image_file(target):
        directory = target.parent
        selected_path = target
        images = [target]
    else:
        raise HTTPException(status_code=422, detail="Selected path is not a directory or supported image file")
    return {
        "directoryPath": str(directory),
        "selectedPath": str(selected_path) if selected_path else (str(images[0]) if images else None),
        "images": [{"name": str(image.relative_to(directory)), "path": str(image)} for image in images],
    }


def serve_image(raw_path: str) -> FileResponse:
    target = resolve_filesystem_path(raw_path)
    if not is_image_file(target):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(target)
