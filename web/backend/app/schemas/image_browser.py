from pydantic import BaseModel


class ImageItem(BaseModel):
    name: str
    path: str


class ImageBrowseResponse(BaseModel):
    directoryPath: str
    selectedPath: str | None = None
    images: list[ImageItem]
