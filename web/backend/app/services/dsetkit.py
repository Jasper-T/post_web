from pathlib import Path

from fastapi import HTTPException

from backend.app.schemas.dsetkit import (
    DsetkitConvertRequest,
    DsetkitPlotRequest,
    DsetkitRunResponse,
)


SUPPORTED_FORMATS = ("labelme", "voc", "yolo")
FORMAT_DIRS = {
    "labelme": "labelme",
    "voc": "xmls",
    "yolo": "labels",
}


def normalize_names(raw_names: list[str] | str) -> list[str]:
    if isinstance(raw_names, str):
        candidates = raw_names.replace(",", "\n").splitlines()
    else:
        candidates = raw_names

    names = [str(name).strip() for name in candidates if str(name).strip()]
    if not names:
        raise HTTPException(status_code=422, detail="At least one class name is required")
    return names


def resolve_directory(raw_path: str, *, field_name: str, must_exist: bool = True) -> Path:
    path = Path(raw_path).expanduser().resolve(strict=False)

    if must_exist and not path.is_dir():
        raise HTTPException(status_code=404, detail=f"{field_name} is not a directory")

    return path


def resolve_output_directory(raw_path: str | None, fallback_parent: Path, name: str | None = None) -> Path:
    if raw_path:
        return Path(raw_path).expanduser().resolve(strict=False)

    if name is None:
        return fallback_parent

    return fallback_parent / name


def reject_existing_output_directory(path: Path) -> None:
    if path.exists():
        raise HTTPException(status_code=409, detail=f"Output directory already exists: {path}")


def convert_target_directory(out_dir: Path, target_format: str) -> Path:
    return out_dir / FORMAT_DIRS[target_format]


def get_tools_payload() -> dict:
    return {
        "formats": list(SUPPORTED_FORMATS),
        "tools": [
            {
                "id": "convert",
                "name": "标注格式转换",
                "description": "批量转换 LabelMe / VOC / YOLO 标注格式。",
                "requiresTargetFormat": True,
            },
            {
                "id": "plot",
                "name": "标注可视化",
                "description": "把标注框绘制到图像上并批量导出。",
                "requiresTargetFormat": False,
            },
        ],
    }


def run_convert(request: DsetkitConvertRequest) -> DsetkitRunResponse:
    image_dir = resolve_directory(request.imageDir, field_name="imageDir")
    label_dir = resolve_directory(request.labelDir, field_name="labelDir")
    out_dir = resolve_output_directory(
        request.outDir,
        fallback_parent=label_dir.parent,
    )
    names = normalize_names(request.names)
    target_dir = convert_target_directory(out_dir, request.targetFormat)
    reject_existing_output_directory(target_dir)

    try:
        from dsetkit.tools import convert_dirs

        convert_dirs(
            image_dir=image_dir,
            label_dir=label_dir,
            source_format=request.sourceFormat,
            target_format=request.targetFormat,
            names=names,
            out_dir=out_dir,
        )
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="dsetkit is not importable by the backend") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Convert failed: {exc}") from exc

    return DsetkitRunResponse(
        tool="convert",
        status="success",
        message="标注格式转换已完成。",
        outputDir=str(target_dir),
    )


def run_plot(request: DsetkitPlotRequest) -> DsetkitRunResponse:
    image_dir = resolve_directory(request.imageDir, field_name="imageDir")
    label_dir = resolve_directory(request.labelDir, field_name="labelDir")
    out_dir = resolve_output_directory(
        request.outDir,
        fallback_parent=label_dir.parent,
        name="annotations",
    )
    names = normalize_names(request.names)
    reject_existing_output_directory(out_dir)

    try:
        from dsetkit.tools import plot_dirs

        plot_dirs(
            image_dir=image_dir,
            label_dir=label_dir,
            source_format=request.sourceFormat,
            names=names,
            out_dir=out_dir,
        )
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="dsetkit visualize dependencies are not importable") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Plot failed: {exc}") from exc

    return DsetkitRunResponse(
        tool="plot",
        status="success",
        message="标注可视化已完成。",
        outputDir=str(out_dir),
    )
