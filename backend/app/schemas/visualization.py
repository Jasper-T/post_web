from typing import Any, Literal

from pydantic import BaseModel, Field


class GeneratePredRequest(BaseModel):
    imagePath: str = Field(..., min_length=1)
    parsed: Any = Field(default_factory=list)


class VisualizationItem(BaseModel):
    imagePath: str
    cachePath: str | None = None
    savedPath: str | None = None
    error: str | None = None


class VisualizationResponse(BaseModel):
    status: Literal["success"] = "success"
    items: list[VisualizationItem] = Field(default_factory=list)


class GenerateGTRequest(BaseModel):
    imagePaths: list[str] = Field(default_factory=list)
    labelDir: str
    format: Literal["yolo", "labelme", "voc"]
    names: list[str] = Field(default_factory=list)
