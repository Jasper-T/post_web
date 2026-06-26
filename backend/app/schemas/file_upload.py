from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    originalName: str
    relativePath: str
    path: str
    renamed: bool
    size: int
