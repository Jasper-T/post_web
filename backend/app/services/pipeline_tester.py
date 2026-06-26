from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import HTTPException
from loguru import logger

from backend.pipeline_core.api_pipeline import ResponseParserConfig
from backend.pipeline_core.protocols import ResponseParseError
from backend.pipeline_core import (
    DELETED_GROUP_NAME,
    UNGROUPED_GROUP_NAME,
    build_pipeline_bundle,
    create_pipeline_group,
    delete_pipeline_group,
    get_group_pipeline_asset_dir,
    get_group_pipeline_dir,
    get_pipeline_definition,
    get_pipeline_groups,
    get_pipeline_names,
    move_pipeline_to_deleted_group,
    normalize_group_name,
    remove_pipeline_definition,
    reassign_group_members,
    rename_pipeline_definition,
    rename_pipeline_group,
    save_pipeline_definition,
    update_pipeline_definition_assets,
    update_pipeline_definition_group,
)
from backend.pipeline_core.registry import DATA_ROOT, TEMPLATES_DIR
from backend.app.services.visualization import (
    clear_pred_cache,
    get_pred_cache_path,
    get_pred_saved_path,
    render_pred_cache,
    sync_pred_cache,
)
from backend.app.schemas.pipeline_tester import (
    PipelineAssetResponse,
    PipelineAssetSaveRequest,
    PipelineEditor,
    PipelineGroupCreateRequest,
    PipelineGroupMoveRequest,
    PipelineGroupRenameRequest,
    PipelineGroupSummary,
    PipelineListResponse,
    PipelineRunResultsResponse,
    PipelineTemplateCatalogResponse,
    PipelineSummary,
    ResponseMapping,
    RunPipelineItem,
    RunPipelineRequest,
    RunPipelineResponse,
    SavePipelineResponse,
    TemplateSummary,
)


PROJECT_ROOT = DATA_ROOT
REQUEST_TEMPLATE_DIR = TEMPLATES_DIR / "requests"
RESPONSE_TEMPLATE_DIR = TEMPLATES_DIR / "responses"
RESULTS_ROOT = DATA_ROOT / "results"
RUN_OUTPUT_DIR = RESULTS_ROOT
RUN_OUTPUT_BUCKET_HOURS = 2
RUN_OUTPUT_RETENTION_FOLDERS = 6
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def list_pipelines() -> PipelineListResponse:
    items = []
    definitions = get_pipeline_names()
    counts: dict[str, int] = {}
    for name, definition in sorted(definitions.items()):
        group_name = normalize_group_name(definition.group_name)
        counts[group_name] = counts.get(group_name, 0) + 1
        items.append(
            PipelineSummary(
                name=name,
                displayName=definition.display_name,
                groupName=group_name,
                url=definition.url,
                method=definition.method,
            )
        )
    groups = [
        PipelineGroupSummary(name=group_name, count=counts.get(group_name, 0))
        for group_name in get_pipeline_groups()
    ]
    return PipelineListResponse(items=items, groups=groups)


def list_pipeline_templates() -> PipelineTemplateCatalogResponse:
    return PipelineTemplateCatalogResponse(
        requests=_scan_template_dir(REQUEST_TEMPLATE_DIR, "request"),
        responses=_scan_template_dir(RESPONSE_TEMPLATE_DIR, "response"),
    )


def get_pipeline_editor(name: str) -> PipelineEditor:
    try:
        definition = get_pipeline_definition(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {name}") from exc

    _validate_editor_dependencies(definition)

    header_template = _read_optional_project_json(definition.header_json)
    body_template = _read_optional_project_json(definition.body_json)
    response_template = _read_optional_project_json(definition.response_template_json)
    response_map = _read_optional_project_json(definition.response_map_json)
    post_config = _read_optional_project_json(definition.post_config_json)
    response_config = definition.response_config
    response_rules = _read_optional_project_json(response_config.rule_json) if response_config else {}
    response_mapping = _map_payload_to_response_mapping(response_map) or _rules_to_response_mapping(response_rules or {})
    image_field_path, image_source = _detect_image_field(body_template or {})
    default_inputs = definition.default_inputs or {}

    return PipelineEditor(
        name=definition.name,
        displayName=definition.display_name,
        groupName=normalize_group_name(definition.group_name),
        url=definition.url,
        method=definition.method,
        transport=definition.transport,
        imageDirectory=None,
        headerTemplate=header_template or {},
        bodyTemplate=body_template or {},
        imageFieldPath=image_field_path,
        imageSource=image_source,
        responseMapping=response_mapping,
        defaultHeaders=default_inputs.get("headers") or {},
        defaultBody=default_inputs.get("body") or {},
        defaultExtra=default_inputs.get("extra") or {},
        templateInput=response_template or (response_config.template_input if response_config else None),
        postConfig=post_config or {},
        assetPaths={
            "header": definition.header_json,
            "body": definition.body_json,
            "response": definition.response_template_json,
            "mapping": definition.response_map_json,
            "post_config": definition.post_config_json,
        },
        connectTimeout=definition.connect_timeout,
        readTimeout=definition.read_timeout,
    )


def _validate_editor_dependencies(definition) -> None:
    has_mapping_dependency = bool(definition.response_map_json)
    has_post_config_dependency = bool(definition.post_config_json)
    if not (has_mapping_dependency or has_post_config_dependency):
        return

    missing = []
    if not _project_json_exists(definition.body_json):
        missing.append("body.json")
    if not _project_json_exists(definition.response_template_json):
        missing.append("response.json")
    if missing:
        dependencies = []
        if has_mapping_dependency:
            dependencies.append("mapping")
        if has_post_config_dependency:
            dependencies.append("post_config")
        raise HTTPException(
            status_code=422,
            detail=(
                f"Pipeline `{definition.name}` has {', '.join(dependencies)} config, "
                f"but missing required dependency file(s): {', '.join(missing)}"
            ),
        )



def _validate_pipeline_save_dependencies(editor: PipelineEditor) -> None:
    normalized_mapping = _normalize_response_mapping(editor.responseMapping)
    has_body = _has_json_content(editor.bodyTemplate) or bool(editor.assetPaths.get("body"))
    has_response = _has_json_content(editor.templateInput) or bool(editor.assetPaths.get("response"))
    has_mapping = bool(editor.assetPaths.get("mapping")) or _is_meaningful_mapping(normalized_mapping)
    has_post_config = bool(editor.assetPaths.get("post_config")) or _is_meaningful_post_config(editor.postConfig)
    if (has_mapping or has_post_config) and not (has_body and has_response):
        raise HTTPException(
            status_code=400,
            detail="Body JSON and Response JSON are required when Mapping or Post Config is configured",
        )


def save_pipeline(editor: PipelineEditor) -> SavePipelineResponse:
    _validate_pipeline_save_dependencies(editor)
    original_name = (editor.originalName or "").strip()
    if original_name and original_name != editor.name:
        try:
            rename_pipeline_definition(original_name, editor.name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Pipeline not found: {original_name}") from exc
        except FileExistsError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    normalized_group = normalize_group_name(editor.groupName)
    create_pipeline_group(normalized_group)
    pipeline_dir = get_group_pipeline_dir(normalized_group, editor.name)
    asset_dir = pipeline_dir
    pipeline_dir.mkdir(parents=True, exist_ok=True)

    header_path = asset_dir / "header.json"
    body_path = asset_dir / "body.json"
    response_path = asset_dir / "response.json"
    map_path = asset_dir / "mapping.json"
    post_config_path = asset_dir / "post_config.json"
    rule_path = pipeline_dir / "rule.json"

    normalized_mapping = _normalize_response_mapping(editor.responseMapping)
    response_rules = _response_mapping_to_rules(normalized_mapping)
    has_header = _has_json_content(editor.headerTemplate) or bool(editor.assetPaths.get("header"))
    has_body = _has_json_content(editor.bodyTemplate) or bool(editor.assetPaths.get("body"))
    has_response = _has_json_content(editor.templateInput) or bool(editor.assetPaths.get("response"))
    has_mapping = bool(editor.assetPaths.get("mapping")) or _is_meaningful_mapping(normalized_mapping)
    has_post_config = bool(editor.assetPaths.get("post_config")) or _is_meaningful_post_config(editor.postConfig)

    if (has_mapping or has_post_config) and not (has_body and has_response):
        raise HTTPException(
            status_code=400,
            detail="Body JSON and Response JSON are required when Mapping or Post Config is configured",
        )

    header_json = _write_optional_json(header_path, editor.headerTemplate or {}, True)
    body_json = _write_optional_json(body_path, editor.bodyTemplate or {}, True)
    response_template_json = _write_optional_json(response_path, editor.templateInput or {}, True)
    response_map_json = _write_optional_json(map_path, _response_mapping_to_storage_payload(normalized_mapping), True)
    post_config_json = _write_optional_json(post_config_path, editor.postConfig or {}, True)
    rule_json = _write_optional_json(rule_path, response_rules, has_mapping)

    default_inputs = {
        "headers": editor.defaultHeaders or None,
        "body": editor.defaultBody or None,
        "extra": editor.defaultExtra or None,
    }

    save_pipeline_definition(
        name=editor.name,
        display_name=editor.displayName,
        group_name=normalized_group,
        url=editor.url,
        transport=editor.transport,
        method=editor.method,
        image_directory=None,
        header_json=header_json,
        body_json=body_json,
        response_template_json=response_template_json,
        response_map_json=response_map_json,
        post_config_json=post_config_json,
        default_inputs={key: value for key, value in default_inputs.items() if value},
        response_config=ResponseParserConfig(rule_json=rule_json, template_input=None) if rule_json else None,
        connect_timeout=editor.connectTimeout,
        read_timeout=editor.readTimeout,
        overwrite=True,
    )

    return SavePipelineResponse(
        status="success",
        message="Pipeline saved successfully",
        pipeline=get_pipeline_editor(editor.name),
    )


def save_pipeline_asset(request: PipelineAssetSaveRequest) -> PipelineAssetResponse:
    target_path = _build_asset_path(
        group_name=request.groupName,
        display_name=request.displayName,
        file_name=request.fileName,
    )
    _write_json(target_path, request.content)

    if request.pipelineName:
        asset_field = {
            "header.json": "header_json",
            "body.json": "body_json",
            "response.json": "response_template_json",
            "mapping.json": "response_map_json",
            "post_config.json": "post_config_json",
        }.get(target_path.name)
        if asset_field:
            try:
                timeout_kwargs: dict[str, float] = {}
                if asset_field == "post_config_json":
                    if request.content.get("connectTimeout") is not None:
                        timeout_kwargs["connect_timeout"] = float(request.content["connectTimeout"])
                    if request.content.get("readTimeout") is not None:
                        timeout_kwargs["read_timeout"] = float(request.content["readTimeout"])
                response_rule_json = None
                if asset_field == "response_map_json":
                    mapping = _map_payload_to_response_mapping(request.content)
                    if mapping is None:
                        raise HTTPException(status_code=400, detail="Mapping content is empty")
                    definition = get_pipeline_definition(request.pipelineName)
                    rule_path = get_group_pipeline_dir(definition.group_name, request.pipelineName) / "rule.json"
                    _write_json(rule_path, _response_mapping_to_rules(mapping))
                    response_rule_json = _to_project_relative(rule_path)
                update_pipeline_definition_assets(
                    request.pipelineName,
                    asset_paths={asset_field: _to_project_relative(target_path)},
                    response_rule_json=response_rule_json,
                    **timeout_kwargs,
                )
            except KeyError:
                # Assets can be prepared before the pipeline itself is first saved.
                pass

    return PipelineAssetResponse(
        status="success",
        message="Asset saved successfully",
        path=str(target_path),
        content=request.content,
        text=json.dumps(request.content, ensure_ascii=False, indent=2),
    )


def read_pipeline_asset(
    *,
    path: str | None = None,
    group_name: str | None = None,
    display_name: str | None = None,
    file_name: str | None = None,
) -> PipelineAssetResponse:
    target_path = _resolve_asset_path(path=path, group_name=group_name, display_name=display_name, file_name=file_name)
    content = _read_json(target_path)
    return PipelineAssetResponse(
        status="success",
        message="Asset loaded successfully",
        path=str(target_path),
        content=content,
        text=json.dumps(content, ensure_ascii=False, indent=2),
    )


def add_pipeline_group(request: PipelineGroupCreateRequest) -> PipelineListResponse:
    create_pipeline_group(request.name)
    return list_pipelines()


def update_pipeline_group_name(name: str, request: PipelineGroupRenameRequest) -> PipelineListResponse:
    normalized_group = normalize_group_name(name)
    if normalized_group == DELETED_GROUP_NAME:
        raise HTTPException(status_code=400, detail="Deleted group cannot be renamed")
    try:
        rename_pipeline_group(normalized_group, request.name)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return list_pipelines()


def remove_pipeline_group(name: str) -> PipelineListResponse:
    normalized_group = normalize_group_name(name)
    if normalized_group == DELETED_GROUP_NAME:
        raise HTTPException(status_code=400, detail="Deleted group cannot be removed")
    reassign_group_members(normalized_group, UNGROUPED_GROUP_NAME)
    delete_pipeline_group(normalized_group)
    return list_pipelines()


def move_pipeline_to_group(name: str, request: PipelineGroupMoveRequest) -> PipelineListResponse:
    normalized_group_name = normalize_group_name(request.groupName)
    create_pipeline_group(normalized_group_name)
    update_pipeline_definition_group(name, normalized_group_name)
    return list_pipelines()


def delete_pipeline(name: str, permanent: bool = False) -> PipelineListResponse:
    try:
        definition = get_pipeline_definition(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {name}") from exc

    if permanent:
        try:
            remove_pipeline_definition(name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        create_pipeline_group(DELETED_GROUP_NAME)
        return list_pipelines()

    move_pipeline_to_deleted_group(name)
    create_pipeline_group(DELETED_GROUP_NAME)
    return list_pipelines()


def load_pipeline_run_results(
    name: str,
    input_path: str | None = None,
    run_folder: str | None = None,
) -> PipelineRunResultsResponse:
    try:
        get_pipeline_definition(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {name}") from exc

    result_root = (RESULTS_ROOT / name / "post").resolve(strict=False)
    if not result_root.exists():
        return PipelineRunResultsResponse(pipelineName=name, items=[])

    if run_folder:
        source_dir = Path(run_folder).resolve(strict=False)
        if source_dir != result_root and result_root not in source_dir.parents:
            raise HTTPException(status_code=403, detail="Result folder is outside the current pipeline post directory")
        if not source_dir.exists() or not source_dir.is_dir():
            raise HTTPException(status_code=404, detail="Result folder does not exist")
    else:
        run_directories = [path for path in result_root.iterdir() if path.is_dir()]
        if not run_directories:
            return PipelineRunResultsResponse(pipelineName=name, items=[])
        source_dir = max(run_directories, key=lambda path: path.name)

    summary_path = source_dir / "_summary.json"
    if not summary_path.is_file():
        return PipelineRunResultsResponse(pipelineName=name, items=[])
    summary = _read_json(summary_path)

    allowed_paths: set[str] | None = None
    unique_names: dict[str, str] = {}
    if input_path:
        target = Path(input_path).resolve(strict=False)
        if target.exists():
            paths = _collect_image_paths(target)
            allowed_paths = {str(path) for path in paths}
            counts: dict[str, int] = {}
            for path in paths:
                counts[path.name] = counts.get(path.name, 0) + 1
            unique_names = {path.name: str(path) for path in paths if counts[path.name] == 1}

    items: list[RunPipelineItem] = []
    for metadata in summary.get("items", []):
        try:
            result_file = metadata.get("result_file")
            parsed = _read_json(source_dir / result_file) if result_file else None
            item = RunPipelineItem(
                imagePath=metadata["image_path"],
                ok=metadata.get("ok", False),
                elapsedMs=metadata.get("elapsed_ms"),
                parsed=parsed,
                error=metadata.get("error"),
                predCachePath=get_pred_cache_path(name, metadata["image_path"]),
                predSavedPath=get_pred_saved_path(name, metadata["image_path"]),
            )
        except Exception:
            continue

        item_path = str(Path(item.imagePath).resolve(strict=False))
        if allowed_paths is not None and item_path not in allowed_paths:
            fallback = unique_names.get(Path(item.imagePath).name)
            if fallback is None:
                continue
            item = item.model_copy(update={"imagePath": fallback})
        items.append(item)

    items.sort(key=lambda item: item.imagePath)
    return PipelineRunResultsResponse(pipelineName=name, items=items)


def run_pipeline(name: str, request: RunPipelineRequest) -> RunPipelineResponse:
    input_path = Path(request.inputPath).resolve(strict=False)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Input path does not exist")

    bundle = build_pipeline_bundle(name=name, storage_dir=None)
    plot_fields = _get_pipeline_plot_fields(name)
    image_paths = _collect_image_paths(input_path)
    if request.limit is not None:
        image_paths = image_paths[: request.limit]
    if not image_paths:
        raise HTTPException(status_code=422, detail="No images found in the selected path")

    if request.clearVisualizationCache and not request.saveResults:
        clear_pred_cache(name)

    run_dir = None
    if request.saveResults:
        timestamp = _run_bucket_name(datetime.now())
        run_dir = RESULTS_ROOT / name / "post" / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        _prune_run_directories(run_dir.parent, keep=RUN_OUTPUT_RETENTION_FOLDERS)

    items: list[RunPipelineItem] = []
    summary_items: list[dict[str, Any]] = []
    if run_dir is not None and (run_dir / "_summary.json").is_file():
        try:
            summary_items = list(_read_json(run_dir / "_summary.json").get("items", []))
        except Exception:
            summary_items = []
    succeeded = 0
    failed = 0

    for image_path in image_paths:
        started_at = perf_counter()
        raw_response: dict[str, Any] | None = None
        result_file: str | None = None
        try:
            raw_response = bundle.run_json(image_path)
            try:
                parsed = bundle.parse_response(json_data=raw_response)
            except ResponseParseError as exc:
                logger.error(
                    "Response parse failed pipeline_name={} image_path={} error={} response_data={}",
                    name, image_path, exc, _format_parse_failure_data(raw_response),
                )
                raise

            pred_cache_path = None
            try:
                pred_cache_path = render_pred_cache(name, str(image_path), parsed, plot_fields)
            except Exception as plot_exc:
                logger.exception("Pred visualization failed pipeline_name={} image_path={} error={}", name, image_path, plot_exc)

            item = RunPipelineItem(
                imagePath=str(image_path),
                ok=True,
                elapsedMs=round((perf_counter() - started_at) * 1000, 3),
                parsed=parsed,
                rawResponse=raw_response,
                predCachePath=pred_cache_path,
            )
            if run_dir is not None:
                result_file = _write_parsed_result(run_dir, image_path, parsed)
            succeeded += 1
        except Exception as exc:
            pred_cache_path = None
            try:
                pred_cache_path = render_pred_cache(name, str(image_path), [], plot_fields)
            except Exception as plot_exc:
                logger.exception("Original image cache failed pipeline_name={} image_path={} error={}", name, image_path, plot_exc)
            item = RunPipelineItem(
                imagePath=str(image_path),
                ok=False,
                elapsedMs=round((perf_counter() - started_at) * 1000, 3),
                rawResponse=raw_response,
                error=str(exc),
                predCachePath=pred_cache_path,
            )
            failed += 1

        items.append(item)
        summary_items = [entry for entry in summary_items if entry.get("image_path") != item.imagePath]
        summary_items.append({
            "image_path": item.imagePath,
            "ok": item.ok,
            "elapsed_ms": item.elapsedMs,
            "error": item.error,
            "result_file": result_file,
        })

    if run_dir is not None:
        _write_json(run_dir / "_summary.json", {
            "pipeline_name": name,
            "input_path": str(input_path),
            "processed": len(summary_items),
            "succeeded": sum(1 for entry in summary_items if entry.get("ok")),
            "failed": sum(1 for entry in summary_items if not entry.get("ok")),
            "items": summary_items,
        })
        sync_pred_cache(
            name,
            [entry["image_path"] for entry in summary_items if entry.get("image_path")],
        )

    return RunPipelineResponse(
        status="success",
        message="Pipeline batch run completed",
        pipelineName=name,
        inputPath=str(input_path),
        processed=len(items),
        succeeded=succeeded,
        failed=failed,
        savedDirectory=str(run_dir) if run_dir is not None else None,
        items=items,
    )


def _get_pipeline_plot_fields(name: str) -> list[str]:
    definition = get_pipeline_definition(name)
    mapping = _read_optional_project_json(definition.response_map_json)
    if isinstance(mapping, dict) and isinstance(mapping.get("plotFields"), list):
        return [str(field) for field in mapping["plotFields"] if str(field)]
    rules = _read_optional_project_json(definition.response_config.rule_json) if definition.response_config else {}
    if isinstance(rules, dict) and isinstance(rules.get("plot_fields"), list):
        return [str(field) for field in rules["plot_fields"] if str(field)]
    return ["label", "conf"]


def _run_bucket_name(value: datetime) -> str:
    bucket_hour = value.hour - (value.hour % RUN_OUTPUT_BUCKET_HOURS)
    return value.replace(hour=bucket_hour, minute=0, second=0, microsecond=0).strftime("%Y%m%d_%H")


def _prune_run_directories(pipeline_run_dir: Path, keep: int) -> None:
    if keep < 1 or not pipeline_run_dir.exists():
        return

    run_directories = sorted(
        (path for path in pipeline_run_dir.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    )
    for stale_dir in run_directories[keep:]:
        try:
            shutil.rmtree(stale_dir)
        except OSError:
            logger.exception("Failed to remove stale pipeline run directory path={}", stale_dir)


def _format_parse_failure_data(data: Any) -> str:
    max_chars = int(os.getenv("PARSE_FAILURE_LOG_MAX_CHARS", "50000"))
    sanitized = _redact_base64_values(data)
    try:
        text = json.dumps(sanitized, ensure_ascii=False, default=str)
    except Exception:
        text = repr(sanitized)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}... <truncated {len(text) - max_chars} chars>"


def _redact_base64_values(value: Any, key: str = "") -> Any:
    normalized_key = key.lower().replace("-", "_")
    if "base64" in normalized_key or "b64" in normalized_key:
        return "..." if value not in (None, "") else value
    if isinstance(value, dict):
        return {item_key: _redact_base64_values(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact_base64_values(item) for item in value]
    if isinstance(value, str) and _looks_like_base64(value):
        return "..."
    return value


def _looks_like_base64(value: str) -> bool:
    compact = value.strip()
    if compact.startswith("data:") and ";base64," in compact[:128]:
        return True
    if len(compact) < 512 or len(compact) % 4 != 0:
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\r\n")
    return all(char in allowed for char in compact)


def _write_parsed_result(run_dir: Path, image_path: Path, parsed: Any) -> str:
    digest = hashlib.sha1(str(image_path).encode("utf-8")).hexdigest()[:10]
    file_name = f"{image_path.stem}-{digest}.json"
    _write_json(run_dir / file_name, parsed)
    return file_name


def _collect_image_paths(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() in IMAGE_EXTENSIONS:
            return [input_path]
        return []

    return sorted(
        [
            path
            for path in input_path.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ]
    )


def _rules_to_response_mapping(rules: dict[str, Any]) -> ResponseMapping:
    if not rules:
        return _default_response_mapping()

    bbox = rules.get("bbox") or {}
    bbox_kind = bbox.get("kind")
    bbox_paths = bbox.get("paths") or ["x1", "y1", "x2", "y2"]
    bbox_path = bbox.get("path") or ("bbox" if bbox_kind in {None, "", "passthrough", "xywh_to_xyxy"} else None)
    output_type = rules.get("output_type", "detection")
    normalized_output_type = "detection" if output_type == "detection" else "extra"
    extra_fields = [
        {
            "name": field.get("name"),
            "path": field.get("path"),
            "default": field.get("default"),
            "cast": field.get("cast"),
        }
        for field in rules.get("extra_fields", [])
    ]
    if output_type == "ocr" and "text" in rules:
        text_rule = rules.get("text") or {}
        extra_fields.append(
            {
                "name": "text",
                "path": text_rule.get("path"),
                "default": text_rule.get("default"),
                "cast": text_rule.get("cast"),
            }
        )

    return ResponseMapping(
        outputType=normalized_output_type,
        collectionPaths=rules.get("collection_paths") or ["data.outputs"],
        itemPath=rules.get("item_path"),
        labelPath=(rules.get("label") or {}).get("path"),
        classIdPath=(rules.get("class_id") or {}).get("path"),
        confPath=(rules.get("conf") or {}).get("path"),
        textPath=(rules.get("text") or {}).get("path"),
        bboxMode=bbox_kind or "passthrough",
        bboxInputMode="fields" if bbox_kind in {"xyxy_from_paths", "xywh_from_paths"} else "list",
        bboxCoordinateType="xywh" if bbox_kind in {"xywh_to_xyxy", "xywh_from_paths"} else "xyxy",
        bboxIsCenter=bool(bbox.get("center", False)),
        bboxPath=bbox_path,
        bboxPaths=bbox_paths,
        bboxCast=bbox.get("cast") or "float",
        names=rules.get("names") or [],
        plotFields=rules.get("plot_fields") or ["label", "conf"],
        extraFields=extra_fields,
    )


def _default_response_mapping() -> ResponseMapping:
    return ResponseMapping(
        outputType="detection",
        collectionPaths=["data.outputs"],
        itemPath=None,
        labelPath=None,
        classIdPath=None,
        confPath=None,
        textPath=None,
        bboxMode="passthrough",
        bboxInputMode="list",
        bboxCoordinateType="xyxy",
        bboxIsCenter=False,
        bboxPath=None,
        bboxPaths=[None, None, None, None],
        bboxCast="float",
        names=[],
        plotFields=["label", "conf"],
        extraFields=[],
    )


def _map_payload_to_response_mapping(payload: dict[str, Any] | None) -> ResponseMapping | None:
    if not isinstance(payload, dict) or not payload:
        return None
    return ResponseMapping(**payload)


def _normalize_response_mapping(mapping: ResponseMapping) -> ResponseMapping:
    payload = mapping.model_dump()
    payload["itemPath"] = payload.get("itemPath") or None
    payload["labelPath"] = payload.get("labelPath") or None
    payload["classIdPath"] = payload.get("classIdPath") or None
    payload["confPath"] = payload.get("confPath") or None
    payload["textPath"] = payload.get("textPath") or None
    payload["bboxPath"] = payload.get("bboxPath") or None
    payload["bboxPaths"] = [(path or None) for path in payload.get("bboxPaths", [])]
    normalized_extra_fields = []
    for field in payload.get("extraFields", []):
        normalized_extra_fields.append(
            {
                **field,
                "path": field.get("path") or None,
                "default": field.get("default"),
                "cast": field.get("cast") or None,
            }
        )
    payload["extraFields"] = normalized_extra_fields
    return ResponseMapping(**payload)


def _response_mapping_to_storage_payload(mapping: ResponseMapping) -> dict[str, Any]:
    normalized = _normalize_response_mapping(mapping)
    return normalized.model_dump()


def _response_mapping_to_rules(mapping: ResponseMapping) -> dict[str, Any]:
    mapping = _normalize_response_mapping(mapping)
    rules: dict[str, Any] = {
        "output_type": mapping.outputType,
        "collection_paths": mapping.collectionPaths,
    }

    if mapping.itemPath:
        rules["item_path"] = mapping.itemPath
    if mapping.names:
        rules["names"] = mapping.names
    rules["plot_fields"] = mapping.plotFields

    if mapping.outputType == "detection":
        if mapping.labelPath:
            rules["label"] = {"path": mapping.labelPath}
        if mapping.classIdPath:
            rules["class_id"] = {"path": mapping.classIdPath, "cast": "int"}
        if mapping.confPath:
            rules["conf"] = {"path": mapping.confPath, "cast": "float", "default": 0}
    else:
        return rules

    bbox_kind = (
        "xywh_from_paths"
        if mapping.bboxInputMode == "fields" and mapping.bboxCoordinateType == "xywh"
        else (
            "xyxy_from_paths"
            if mapping.bboxInputMode == "fields"
            else ("xywh_to_xyxy" if mapping.bboxCoordinateType == "xywh" else "passthrough")
        )
    )

    bbox_rule: dict[str, Any] = {
        "kind": bbox_kind,
        "cast": mapping.bboxCast,
    }
    if bbox_kind in {"passthrough", "xywh_to_xyxy"}:
        if mapping.bboxPath:
            bbox_rule["path"] = mapping.bboxPath
            bbox_rule["default"] = []
        else:
            return rules
    else:
        if not all(mapping.bboxPaths):
            return rules
        bbox_rule["paths"] = [path for path in mapping.bboxPaths if path is not None]
        bbox_rule["default"] = 0
    if bbox_kind in {"xywh_to_xyxy", "xywh_from_paths"}:
        bbox_rule["center"] = bool(mapping.bboxIsCenter)
    rules["bbox"] = bbox_rule

    if mapping.extraFields:
        rules["extra_fields"] = [
            {
                key: value
                for key, value in {
                    "name": field.name,
                    "path": field.path,
                    "default": field.default,
                    "cast": field.cast,
                }.items()
                if value is not None
            }
            for field in mapping.extraFields
        ]

    return rules


def _detect_image_field(payload: dict[str, Any]) -> tuple[str, str]:
    for target, source in (("{{image_base64}}", "base64"), ("{{image_url}}", "url")):
        found = _find_path_for_value(payload, target)
        if found is not None:
            return found, source
    return "image", "base64"


def _find_path_for_value(data: Any, target: str, prefix: str = "") -> str | None:
    if isinstance(data, dict):
        for key, value in data.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            found = _find_path_for_value(value, target, next_prefix)
            if found is not None:
                return found
        return None
    if isinstance(data, list):
        for index, value in enumerate(data):
            next_prefix = f"{prefix}.{index}" if prefix else str(index)
            found = _find_path_for_value(value, target, next_prefix)
            if found is not None:
                return found
        return None
    if data == target:
        return prefix
    return None


def _read_optional_project_json(raw_path: str | None) -> dict[str, Any] | None:
    if not raw_path:
        return None
    path = PROJECT_ROOT / raw_path
    if not path.exists():
        return None
    return _read_json(path)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _write_optional_json(path: Path, payload: Any, should_write: bool) -> str | None:
    if not should_write:
        if path.exists():
            path.unlink()
        return None
    _write_json(path, payload)
    return _to_project_relative(path)


def _has_json_content(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def _is_meaningful_mapping(mapping: ResponseMapping) -> bool:
    normalized = _normalize_response_mapping(mapping)
    return any(
        [
            bool(normalized.itemPath),
            bool(normalized.labelPath),
            bool(normalized.classIdPath),
            bool(normalized.confPath),
            bool(normalized.textPath),
            bool(normalized.bboxPath),
            any(normalized.bboxPaths or []),
            bool(normalized.names),
            bool(normalized.extraFields),
        ]
    )


def _is_meaningful_post_config(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    placeholder_paths = value.get("placeholderPaths") or {}
    if isinstance(placeholder_paths, dict) and any(placeholder_paths.values()):
        return True
    return False


def _project_json_exists(raw_path: str | None) -> bool:
    if not raw_path:
        return False
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / raw_path
    return path.exists() and path.suffix.lower() == ".json"


def _build_asset_path(*, group_name: str | None, display_name: str, file_name: str) -> Path:
    safe_name = _normalize_asset_file_name(file_name)
    return get_group_pipeline_asset_dir(normalize_group_name(group_name), display_name) / safe_name


def _resolve_asset_path(
    *,
    path: str | None = None,
    group_name: str | None = None,
    display_name: str | None = None,
    file_name: str | None = None,
) -> Path:
    if path:
        target_path = Path(path)
        if not target_path.is_absolute():
            target_path = PROJECT_ROOT / target_path
    else:
        if not display_name or not file_name:
            raise HTTPException(status_code=422, detail="displayName and fileName are required")
        target_path = _build_asset_path(group_name=group_name, display_name=display_name, file_name=file_name)

    resolved = target_path.resolve(strict=False)
    project_root = PROJECT_ROOT.resolve()
    if project_root not in {resolved, *resolved.parents}:
        raise HTTPException(status_code=400, detail="Path is outside the project root")
    if resolved.suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="Only JSON files are supported")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {resolved}")
    return resolved


def _normalize_asset_file_name(file_name: str) -> str:
    name = file_name.strip().replace("\\", "_").replace("/", "_")
    if not name.endswith(".json"):
        name = f"{name}.json"
    return name


def _to_project_relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _scan_template_dir(directory: Path, category: str) -> list[TemplateSummary]:
    if not directory.exists():
        return []

    items = []
    for path in sorted(directory.rglob("*.json")):
        relative_path = path.resolve().relative_to(PROJECT_ROOT).as_posix()
        items.append(
            TemplateSummary(
                name=path.stem,
                path=relative_path,
                category=category,
            )
        )
    return items
