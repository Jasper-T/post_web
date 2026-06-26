from typing import Literal

from pydantic import BaseModel


class FileNode(BaseModel):
    name: str
    path: str
    type: Literal["directory", "file"]
    hasChildren: bool
    childrenLoaded: bool = False


class TreeResponse(BaseModel):
    path: str
    children: list[FileNode]
    offset: int = 0
    limit: int = 20
    hasMore: bool = False
