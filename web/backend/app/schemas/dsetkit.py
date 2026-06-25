from typing import Literal

from pydantic import BaseModel, Field


DatasetFormat = Literal["labelme", "voc", "yolo"]
ToolId = Literal["convert", "plot"]


class DsetkitTool(BaseModel):
    id: ToolId
    name: str
    description: str
    requiresTargetFormat: bool = False


class DsetkitToolsResponse(BaseModel):
    formats: list[DatasetFormat]
    tools: list[DsetkitTool]


class DsetkitBaseRequest(BaseModel):
    imageDir: str = Field(..., min_length=1)
    labelDir: str = Field(..., min_length=1)
    sourceFormat: DatasetFormat
    names: list[str] | str = Field(default_factory=list)
    outDir: str | None = None


class DsetkitConvertRequest(DsetkitBaseRequest):
    targetFormat: DatasetFormat


class DsetkitPlotRequest(DsetkitBaseRequest):
    pass


class DsetkitRunResponse(BaseModel):
    tool: ToolId
    status: Literal["success"]
    message: str
    outputDir: str | None = None
