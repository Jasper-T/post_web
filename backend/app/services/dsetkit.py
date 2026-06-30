from datetime import datetime
from pathlib import Path
import tempfile

from fastapi import HTTPException

from backend.pipeline_core.registry import DATA_ROOT

from backend.app.schemas.dsetkit import (
    DsetkitConvertRequest,
    DsetkitEvaluateRequest,
    DsetkitEvaluateResponse,
    DsetkitPlotRequest,
    DsetkitPredConvertRequest,
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


def normalize_prediction_items(parsed, names: list[str], *, include_conf: bool = True) -> list[dict]:
    items = parsed if isinstance(parsed, list) else [parsed]
    predictions = []

    for item in items:
        if not isinstance(item, dict):
            continue

        bbox = item.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue

        try:
            normalized_bbox = [float(value) for value in bbox]
        except (TypeError, ValueError):
            continue

        class_id = None
        label = item.get("label")
        if item.get("class_id") is not None:
            try:
                class_id = int(item.get("class_id"))
            except (TypeError, ValueError):
                class_id = None
        if not label and class_id is not None:
            label = names[class_id] if 0 <= class_id < len(names) else None
        if label and class_id is None and str(label) in names:
            class_id = names.index(str(label))

        if not label and class_id is None:
            continue

        record = {"bbox": normalized_bbox}
        if label:
            record["label"] = str(label)
        if class_id is not None:
            record["class_id"] = class_id
        if include_conf:
            try:
                record["conf"] = float(item.get("conf", 1.0))
            except (TypeError, ValueError):
                record["conf"] = 1.0
        predictions.append(record)

    return predictions



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

def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def pred_convert_output_directory(raw_path: str | None, target_format: str) -> tuple[Path, Path]:
    out_dir = resolve_output_directory(
        raw_path,
        fallback_parent=DATA_ROOT / "conversions" / "pred" / _timestamp(),
    )
    target_dir = convert_target_directory(out_dir, target_format)
    return out_dir, target_dir


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


def run_pred_convert(request: DsetkitPredConvertRequest) -> DsetkitRunResponse:
    names = normalize_names(request.names)
    predictions_by_image = [
        (
            Path(item.imagePath).expanduser().resolve(strict=False),
            normalize_prediction_items(item.parsed, names, include_conf=False),
        )
        for item in request.predictions
    ]
    predictions_by_image = [(image_path, records) for image_path, records in predictions_by_image if records]
    if not predictions_by_image:
        raise HTTPException(status_code=422, detail="At least one parsed prediction is required")

    out_dir, target_dir = pred_convert_output_directory(request.outDir, request.targetFormat)
    reject_existing_output_directory(target_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from dsetkit.annotations.io import convert, dump
        from dsetkit.annotations.schema import Annotation, AnnotationItem, BBox
        from dsetkit.utils.image import read_image_info

        with tempfile.TemporaryDirectory(prefix="fuxing-pred-convert-") as tmp:
            source_dir = Path(tmp) / "labelme"
            source_dir.mkdir(parents=True, exist_ok=True)
            for image_path, records in predictions_by_image:
                if not image_path.is_file():
                    raise ValueError(f"Image does not exist: {image_path}")
                info = read_image_info(image_path)
                ann = Annotation(
                    width=info.width,
                    height=info.height,
                    names=names,
                    extra={"imagePath": image_path.name, "image_path": str(image_path)},
                )
                for record in records:
                    class_id = record.get("class_id")
                    label = record.get("label") or (names[class_id] if class_id is not None and 0 <= class_id < len(names) else str(class_id))
                    x1, y1, x2, y2 = record["bbox"]
                    ann.items.append(
                        AnnotationItem(
                            category=str(label),
                            category_id=class_id,
                            bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                            extra={"shape_type": "rectangle"},
                        )
                    )
                source_path = source_dir / f"{image_path.stem}.json"
                dump(ann, str(source_path), fmt="labelme")
                convert(
                    label_path=str(source_path),
                    image_path=str(image_path),
                    source_format="labelme",
                    target_format=request.targetFormat,
                    names=names,
                    out_dir=str(out_dir),
                )
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="dsetkit convert dependencies are not importable") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pred convert failed: {exc}") from exc

    return DsetkitRunResponse(
        tool="convert",
        status="success",
        message="Pred annotations converted.",
        outputDir=str(target_dir),
    )


def run_evaluate(request: DsetkitEvaluateRequest) -> DsetkitEvaluateResponse:
    image_dir = resolve_directory(request.imageDir, field_name="imageDir")
    label_dir = resolve_directory(request.labelDir, field_name="labelDir")
    names = normalize_names(request.names)
    predictions_by_image = {
        str(Path(item.imagePath).expanduser().resolve(strict=False)): normalize_prediction_items(item.parsed, names)
        for item in request.predictions
    }

    if not predictions_by_image:
        raise HTTPException(status_code=422, detail="At least one parsed prediction is required")

    try:
        from dsetkit.dataset import Dataset
        from dsetkit.evaluator import Evaluator

        dataset = Dataset(
            names=names,
            image_dir=image_dir,
            label_dir=label_dir,
            source_format=request.sourceFormat,
        )
        dataset.build()
        dataset_stats = dataset.stats().as_dict()
        evaluator = Evaluator(dataset)
        metrics = evaluator.evaluate(
            predictions=predictions_by_image,
            conf_threshold=request.confThreshold,
            iou=request.iouThreshold,
            print_metrics=False,
        )
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="dsetkit evaluator is not importable by the backend") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evaluate failed: {exc}") from exc

    return DsetkitEvaluateResponse(
        tool="evaluate",
        status="success",
        message="Evaluation completed.",
        dataset=dataset_stats,
        metrics=metrics,
        evaluatedImages=len(predictions_by_image),
    )
