from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, AliasChoices, model_validator

from backend.pipeline_core import PIPELINE_NAME_PATTERN


HttpMethod = Literal["POST", "GET", "PUT", "PATCH", "DELETE"]
BBoxMode = Literal["passthrough", "xyxy_from_paths", "xywh_to_xyxy", "xywh_from_paths"]
BBoxInputMode = Literal["list", "fields"]
BBoxCoordinateType = Literal["xyxy", "xywh"]
OutputType = Literal["detection", "extra"]


class ExtraFieldMapping(BaseModel):
    name: str = Field(..., min_length=1)
    path: str | None = None
    default: Any = None
    cast: Literal["int", "float", "str", "bool"] | None = None


class ResponseMapping(BaseModel):
    outputType: OutputType = "detection"
    collectionPaths: list[str] = Field(default_factory=lambda: ["data.outputs"])
    itemPath: str | None = None
    labelPath: str | None = "label"
    classIdPath: str | None = None
    confPath: str | None = "score"
    textPath: str | None = None
    bboxMode: BBoxMode = "passthrough"
    bboxInputMode: BBoxInputMode = "list"
    bboxCoordinateType: BBoxCoordinateType = "xyxy"
    bboxIsCenter: bool = False
    bboxPath: str | None = None
    bboxPaths: list[str | None] = Field(default_factory=lambda: [None, None, None, None])
    bboxCast: Literal["int", "float", "str"] | None = "float"
    names: list[str] = Field(default_factory=list)
    plotFields: list[str] = Field(default_factory=lambda: ["label", "conf"])
    extraFields: list[ExtraFieldMapping] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_paths(self) -> "ResponseMapping":
        if self.outputType != "detection":
            return self
        if self.bboxInputMode == "list" and not self.bboxPath:
            return self
        if self.bboxInputMode == "fields" and len(self.bboxPaths) != 4:
            raise ValueError("bboxPaths must contain exactly 4 entries")
        return self


class PipelineEditor(BaseModel):
    originalName: str | None = Field(default=None, exclude=True)
    name: str = Field(..., min_length=3, max_length=64, pattern=PIPELINE_NAME_PATTERN)
    displayName: str = Field(..., min_length=1)
    groupName: str | None = None
    url: str = Field(..., min_length=1)
    method: HttpMethod = "POST"
    transport: Literal["http"] = "http"
    imageDirectory: str | None = None
    headerTemplate: dict[str, Any] = Field(default_factory=dict)
    bodyTemplate: dict[str, Any] = Field(default_factory=dict)
    imageFieldPath: str = Field(..., min_length=1)
    imageSource: Literal["base64", "url"] = "base64"
    responseMapping: ResponseMapping
    defaultHeaders: dict[str, Any] = Field(default_factory=dict)
    defaultBody: dict[str, Any] = Field(default_factory=dict)
    defaultExtra: dict[str, Any] = Field(default_factory=dict)
    templateInput: dict[str, Any] | None = None
    postConfig: dict[str, Any] = Field(default_factory=dict)
    assetPaths: dict[str, str | None] = Field(default_factory=dict)
    connectTimeout: float = Field(default=3, gt=0)
    readTimeout: float = Field(default=30, gt=0)

    @model_validator(mode="after")
    def validate_pipeline_name(self) -> "PipelineEditor":
        if not self.name.isascii():
            raise ValueError("Pipeline name must use ASCII characters only")
        if self.name[-1] in {"_", "-"}:
            raise ValueError("Pipeline name cannot end with _ or -")
        if "__" in self.name or "--" in self.name or "_-" in self.name or "-_" in self.name:
            raise ValueError("Pipeline name cannot contain consecutive separators")
        return self


class PipelineSummary(BaseModel):
    name: str
    displayName: str
    groupName: str | None = None
    url: str
    method: HttpMethod


class PipelineGroupSummary(BaseModel):
    name: str
    count: int = 0


class PipelineListResponse(BaseModel):
    items: list[PipelineSummary]
    groups: list[PipelineGroupSummary] = Field(default_factory=list)


class PipelineGroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=64, pattern=PIPELINE_NAME_PATTERN)

    @model_validator(mode="after")
    def validate_group_name(self) -> "PipelineGroupCreateRequest":
        validate_name_separators(self.name, "Group name")
        return self


class PipelineGroupRenameRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=64, pattern=PIPELINE_NAME_PATTERN)

    @model_validator(mode="after")
    def validate_group_name(self) -> "PipelineGroupRenameRequest":
        validate_name_separators(self.name, "Group name")
        return self


class PipelineGroupMoveRequest(BaseModel):
    groupName: str | None = None

    @model_validator(mode="after")
    def validate_group_name(self) -> "PipelineGroupMoveRequest":
        if self.groupName:
            validate_name_separators(self.groupName, "Group name")
        return self


def validate_name_separators(value: str, label: str) -> None:
    if not value.isascii():
        raise ValueError(f"{label} must use ASCII characters only")
    if value[-1] in {"_", "-"}:
        raise ValueError(f"{label} cannot end with _ or -")
    if "__" in value or "--" in value or "_-" in value or "-_" in value:
        raise ValueError(f"{label} cannot contain consecutive separators")


class TemplateSummary(BaseModel):
    name: str
    path: str
    category: Literal["request", "response"]


class PipelineTemplateCatalogResponse(BaseModel):
    requests: list[TemplateSummary]
    responses: list[TemplateSummary]


class SavePipelineResponse(BaseModel):
    status: Literal["success"]
    message: str
    pipeline: PipelineEditor


class RunPipelineRequest(BaseModel):
    inputPath: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("inputPath", "imageDirectory"),
    )
    limit: int | None = Field(default=None, ge=1, le=5000)
    saveResults: bool = True
    clearVisualizationCache: bool = False


class RunPipelineItem(BaseModel):
    imagePath: str
    ok: bool
    elapsedMs: float | None = None
    parsed: list[dict[str, Any]] | dict[str, Any] | None = None
    rawResponse: dict[str, Any] | None = None
    error: str | None = None
    predCachePath: str | None = None
    predSavedPath: str | None = None
    gtCachePath: str | None = None
    gtSavedPath: str | None = None


class PipelineRunResultsResponse(BaseModel):
    pipelineName: str
    items: list[RunPipelineItem] = Field(default_factory=list)


class PipelineAssetSaveRequest(BaseModel):
    pipelineName: str | None = None
    groupName: str | None = None
    displayName: str = Field(..., min_length=1)
    fileName: str = Field(..., min_length=1)
    content: dict[str, Any] = Field(default_factory=dict)


class PipelineAssetResponse(BaseModel):
    status: Literal["success"]
    message: str
    path: str
    content: dict[str, Any] = Field(default_factory=dict)
    text: str


class RunPipelineResponse(BaseModel):
    status: Literal["success"]
    message: str
    pipelineName: str
    inputPath: str
    processed: int
    succeeded: int
    failed: int
    savedDirectory: str | None = None
    items: list[RunPipelineItem]
