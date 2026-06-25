import os
import tempfile
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, Request

from backend.app.schemas.file_upload import FileUploadResponse


UPLOAD_ROOT = Path("/data/datasets").resolve(strict=False)


def resolve_upload_directory(raw_directory: str) -> Path:
    directory = Path(raw_directory).resolve(strict=False)
    if directory != UPLOAD_ROOT and UPLOAD_ROOT not in directory.parents:
        raise HTTPException(status_code=403, detail="Uploads are only allowed inside /data/datasets")
    if not directory.exists():
        raise HTTPException(status_code=404, detail="Upload directory does not exist")
    if not directory.is_dir():
        raise HTTPException(status_code=422, detail="Upload target is not a directory")
    return directory


def normalize_relative_path(raw_path: str) -> PurePosixPath:
    normalized = PurePosixPath(str(raw_path or "").replace("\\", "/"))
    if not normalized.parts or normalized.is_absolute() or any(part in {"", ".", ".."} for part in normalized.parts):
        raise HTTPException(status_code=422, detail="Invalid relative upload path")
    return normalized


def reserve_destination(directory: Path, relative_path: PurePosixPath) -> tuple[Path, bool]:
    relative_parent = Path(*relative_path.parts[:-1])
    target_parent = (directory / relative_parent).resolve(strict=False)
    if target_parent != UPLOAD_ROOT and UPLOAD_ROOT not in target_parent.parents:
        raise HTTPException(status_code=403, detail="Upload path is outside /data/datasets")
    target_parent.mkdir(parents=True, exist_ok=True)

    original = Path(relative_path.name)
    stem = original.stem
    suffix = original.suffix
    attempt = 0
    while True:
        filename = original.name if attempt == 0 else f"{stem} ({attempt}){suffix}"
        destination = target_parent / filename
        try:
            descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            attempt += 1
            continue
        os.close(descriptor)
        return destination, attempt > 0


async def upload_file(request: Request, directory: str, relative_path: str) -> FileUploadResponse:
    target_directory = resolve_upload_directory(directory)
    normalized_relative_path = normalize_relative_path(relative_path)
    destination, renamed = reserve_destination(target_directory, normalized_relative_path)
    temporary_path: Path | None = None
    size = 0

    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".upload-", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            async for chunk in request.stream():
                if not chunk:
                    continue
                temporary.write(chunk)
                size += len(chunk)
        os.replace(temporary_path, destination)
    except Exception:
        destination.unlink(missing_ok=True)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise

    return FileUploadResponse(
        originalName=normalized_relative_path.name,
        relativePath=str(normalized_relative_path),
        path=str(destination),
        renamed=renamed,
        size=size,
    )
