import os
import tempfile
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, Request

from backend.app.core.config import DATASETS_ROOT
from backend.app.schemas.file_upload import FileUploadResponse


UPLOAD_ROOT = DATASETS_ROOT


def resolve_upload_directory(raw_directory: str | None = None) -> Path:
    # Uploads are intentionally fixed to DATASETS_ROOT. The browser file picker
    # chooses files from the frontend user's machine; this target is where the
    # backend machine stores them.
    del raw_directory
    directory = UPLOAD_ROOT.resolve(strict=False)
    directory.mkdir(parents=True, exist_ok=True)
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
    upload_root = UPLOAD_ROOT.resolve(strict=False)
    if target_parent != upload_root and upload_root not in target_parent.parents:
        raise HTTPException(status_code=403, detail="Upload path is outside the configured datasets root")
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


async def upload_file(request: Request, directory: str | None, relative_path: str) -> FileUploadResponse:
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
