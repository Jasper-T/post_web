from pydantic import BaseModel
from fastapi import APIRouter, Query

from backend.app.schemas.pipeline_tester import (
    PipelineAssetResponse,
    PipelineAssetSaveRequest,
    PipelineEditor,
    PipelineGroupCreateRequest,
    PipelineGroupMoveRequest,
    PipelineGroupRenameRequest,
    PipelineListResponse,
    PipelineTemplateCatalogResponse,
    RunPipelineRequest,
    RunPipelineResponse,
    PipelineRunResultsResponse,
    SavePipelineResponse,
)
from backend.app.schemas.visualization import (
    GenerateGTRequest,
    GeneratePredRequest,
    VisualizationResponse,
)
from fastapi.responses import FileResponse
from backend.app.services.pipeline_tester import (
    add_pipeline_group,
    delete_pipeline,
    get_pipeline_editor,
    list_pipelines,
    list_pipeline_templates,
    load_pipeline_run_results,
    move_pipeline_to_group,
    read_pipeline_asset,
    remove_pipeline_group,
    run_pipeline,
    save_pipeline_asset,
    save_pipeline,
    render_pipeline_pred_visualization,
    update_pipeline_group_name,
)
from backend.app.services.visualization import delete_pipeline_cache_buckets, generate_gt_cache, list_pipeline_cache_buckets, resolve_visualization_cache_path


router = APIRouter(prefix="/pipelines", tags=["pipelines"])


class DeleteCacheBucketsRequest(BaseModel):
    buckets: list[str] = []


@router.get("", response_model=PipelineListResponse)
def read_pipelines() -> PipelineListResponse:
    return list_pipelines()


@router.post("/groups", response_model=PipelineListResponse)
def create_group(request: PipelineGroupCreateRequest) -> PipelineListResponse:
    return add_pipeline_group(request)


@router.delete("/groups/{name}", response_model=PipelineListResponse)
def delete_group(name: str) -> PipelineListResponse:
    return remove_pipeline_group(name)


@router.patch("/groups/{name}", response_model=PipelineListResponse)
def rename_group(name: str, request: PipelineGroupRenameRequest) -> PipelineListResponse:
    return update_pipeline_group_name(name, request)


@router.get("/templates", response_model=PipelineTemplateCatalogResponse)
def read_pipeline_templates() -> PipelineTemplateCatalogResponse:
    return list_pipeline_templates()


@router.post("/assets", response_model=PipelineAssetResponse)
def create_or_update_pipeline_asset(request: PipelineAssetSaveRequest) -> PipelineAssetResponse:
    return save_pipeline_asset(request)


@router.get("/assets", response_model=PipelineAssetResponse)
def get_pipeline_asset(
    path: str | None = None,
    groupName: str | None = None,
    displayName: str | None = None,
    fileName: str | None = None,
) -> PipelineAssetResponse:
    return read_pipeline_asset(
        path=path,
        group_name=groupName,
        display_name=displayName,
        file_name=fileName,
    )


@router.get("/{name}", response_model=PipelineEditor)
def read_pipeline(name: str) -> PipelineEditor:
    return get_pipeline_editor(name)


@router.post("", response_model=SavePipelineResponse)
def create_or_update_pipeline(request: PipelineEditor) -> SavePipelineResponse:
    return save_pipeline(request)


@router.get("/{name}/results", response_model=PipelineRunResultsResponse)
def read_pipeline_results(
    name: str,
    inputPath: str | None = None,
    runFolder: str | None = None,
) -> PipelineRunResultsResponse:
    return load_pipeline_run_results(name, input_path=inputPath, run_folder=runFolder)


@router.post("/{name}/run", response_model=RunPipelineResponse)
def execute_pipeline(name: str, request: RunPipelineRequest) -> RunPipelineResponse:
    return run_pipeline(name, request)


@router.get("/{name}/cache")
def read_pipeline_cache(name: str) -> dict:
    get_pipeline_editor(name)
    return {"pipelineName": name, "items": list_pipeline_cache_buckets(name)}


@router.delete("/{name}/cache")
def delete_pipeline_cache(name: str, request: DeleteCacheBucketsRequest) -> dict:
    get_pipeline_editor(name)
    return delete_pipeline_cache_buckets(name, request.buckets)


@router.post("/{name}/visualizations/pred", response_model=VisualizationResponse)
def create_pred_visualization(name: str, request: GeneratePredRequest) -> VisualizationResponse:
    get_pipeline_editor(name)
    try:
        cache_path = render_pipeline_pred_visualization(name, request.imagePath, request.parsed)
        item = {"imagePath": request.imagePath, "cachePath": cache_path}
    except Exception as exc:
        item = {"imagePath": request.imagePath, "error": str(exc)}
    return VisualizationResponse(items=[item])


@router.post("/{name}/visualizations/gt", response_model=VisualizationResponse)
def create_gt_visualizations(name: str, request: GenerateGTRequest) -> VisualizationResponse:
    get_pipeline_editor(name)
    return VisualizationResponse(items=generate_gt_cache(name, request.imagePaths, request.labelDir, request.format, request.names))


@router.get("/{name}/visualizations/content")
def read_visualization_content(name: str, path: str = Query(..., description="Absolute visualization cache path")) -> FileResponse:
    get_pipeline_editor(name)
    return FileResponse(resolve_visualization_cache_path(name, path))


@router.post("/{name}/group", response_model=PipelineListResponse)
def update_pipeline_group(name: str, request: PipelineGroupMoveRequest) -> PipelineListResponse:
    return move_pipeline_to_group(name, request)


@router.delete("/{name}", response_model=PipelineListResponse)
def remove_pipeline(name: str, permanent: bool = False) -> PipelineListResponse:
    return delete_pipeline(name, permanent=permanent)
