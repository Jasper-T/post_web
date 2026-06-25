from pathlib import Path

from fastapi import HTTPException
from natsort import natsorted

from backend.app.core.config import FILESYSTEM_ROOT
from backend.app.schemas.file_tree import FileNode, TreeResponse


def resolve_filesystem_path(raw_path: str | None) -> Path:
    path = Path(raw_path or str(FILESYSTEM_ROOT))
    resolved = path.resolve(strict=False)

    filesystem_root = FILESYSTEM_ROOT.resolve(strict=False)
    if resolved != filesystem_root and filesystem_root not in resolved.parents:
        raise HTTPException(status_code=403, detail="Path is outside the allowed data root")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Path does not exist")

    return resolved


def directory_has_children(path: Path) -> bool:
    if not path.is_dir():
        return False

    try:
        next(path.iterdir())
    except StopIteration:
        return False
    except OSError:
        return False

    return True


def to_file_node(path: Path) -> FileNode:
    is_directory = path.is_dir()
    return FileNode(
        name=path.name or str(path),
        path=str(path),
        type="directory" if is_directory else "file",
        hasChildren=directory_has_children(path) if is_directory else False,
    )


def read_directory_tree(
    raw_path: str | None,
    offset: int = 0,
    limit: int = 20,
    filter_text: str | None = None,
) -> TreeResponse:
    target = resolve_filesystem_path(raw_path)
    if not target.is_dir():
        return TreeResponse(path=str(target), children=[], offset=offset, limit=limit, hasMore=False)

    try:
        children = [to_file_node(child) for child in target.iterdir()]
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Permission denied") from exc

    children = natsorted(
        children,
        key=lambda item: (item.type != "directory", item.name),
        alg=0,
    )
    if filter_text:
        children = [child for child in children if filter_text in child.name]

    visible_children = children[offset : offset + limit]
    has_more = offset + limit < len(children)
    return TreeResponse(
        path=str(target),
        children=visible_children,
        offset=offset,
        limit=limit,
        hasMore=has_more,
    )
