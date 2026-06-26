from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from loguru import logger

from backend.app.core.config import DATASETS_ROOT
from backend.pipeline_core.registry import DATA_ROOT


RESULTS_ROOT = DATA_ROOT / "results"
PRED_CACHE_ROOT = RESULTS_ROOT / ".cache"
FORMAT_SUFFIXES = {"yolo": ".txt", "labelme": ".json", "voc": ".xml"}


def clear_all_visualization_caches() -> None:
    _remove_cache_directory(PRED_CACHE_ROOT, allow_pred_root=True)
    if DATASETS_ROOT.exists():
        for cache_dir in DATASETS_ROOT.rglob(".cache"):
            gt_dir = cache_dir / "GT"
            if gt_dir.exists():
                _remove_cache_directory(gt_dir)


def get_pred_saved_path(pipeline_name: str, image_path: str) -> str | None:
    path = RESULTS_ROOT / pipeline_name / "pred" / _visualization_filename(Path(image_path))
    return str(path) if path.is_file() else None


def get_pred_cache_path(pipeline_name: str, image_path: str) -> str | None:
    path = _pred_cache_dir(pipeline_name) / _visualization_filename(Path(image_path))
    return str(path) if path.is_file() else None


def sync_pred_cache(pipeline_name: str, image_paths: list[str]) -> None:
    cache_dir = _pred_cache_dir(pipeline_name)
    if not cache_dir.exists():
        return
    expected_names = {_visualization_filename(Path(image_path)) for image_path in image_paths}
    for child in cache_dir.iterdir():
        if child.is_file() and child.name not in expected_names:
            child.unlink()
        elif child.is_dir():
            raise RuntimeError(f"Unexpected directory in Pred cache: {child}")


def clear_pred_cache(pipeline_name: str) -> None:
    _remove_cache_directory(_pred_cache_dir(pipeline_name))


def render_pred_cache(pipeline_name: str, image_path: str, parsed: Any, plot_fields: list[str] | None = None) -> str | None:
    detections = _normalize_detections(parsed)
    cache_path = _pred_cache_path(pipeline_name, image_path)
    _plot_detections(
        image_path,
        detections,
        plot_fields if plot_fields is not None else ["label", "conf"],
        cache_path,
    )
    return str(cache_path)


def generate_gt_cache(image_paths: list[str], label_dir: str, fmt: str, names: list[str]) -> list[dict[str, Any]]:
    label_root = _resolve_dataset_directory(label_dir)
    cache_dir = label_root.parent / ".cache" / "GT"
    _remove_cache_directory(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    suffix = FORMAT_SUFFIXES[fmt]
    items: list[dict[str, Any]] = []

    for raw_image_path in image_paths:
        try:
            image_path = _resolve_dataset_file(raw_image_path)
            label_path = label_root / f"{image_path.stem}{suffix}"
            if not label_path.is_file():
                raise FileNotFoundError(f"Annotation not found: {label_path.name}")
            output_path = cache_dir / _visualization_filename(image_path)
            _plot_label(image_path, label_path, fmt, names, output_path)
            items.append({"imagePath": str(image_path), "cachePath": str(output_path)})
        except Exception as exc:
            try:
                image_path = _resolve_dataset_file(raw_image_path)
                output_path = cache_dir / _visualization_filename(image_path)
                _plot_detections(image_path, [], [], output_path)
                items.append({"imagePath": str(image_path), "cachePath": str(output_path), "error": str(exc)})
            except Exception as fallback_exc:
                items.append({"imagePath": raw_image_path, "error": f"{exc}; original image fallback failed: {fallback_exc}"})
    return items


def save_visualizations(
    pipeline_name: str,
    kind: str,
    image_paths: list[str],
    label_dir: str | None = None,
) -> list[dict[str, Any]]:
    if kind == "pred":
        cache_dir = _pred_cache_dir(pipeline_name)
        output_dir = RESULTS_ROOT / pipeline_name / "pred"
    else:
        if not label_dir:
            raise HTTPException(status_code=422, detail="labelDir is required for GT")
        label_root = _resolve_dataset_directory(label_dir)
        cache_dir = label_root.parent / ".cache" / "GT"
        output_dir = label_root.parent / "GT"

    output_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for raw_image_path in image_paths:
        try:
            image_path = Path(raw_image_path).resolve(strict=False)
            cache_path = cache_dir / _visualization_filename(image_path)
            if not cache_path.is_file():
                if not image_path.is_file():
                    raise FileNotFoundError("Original image is missing")
                _plot_detections(image_path, [], [], cache_path)
            saved_path = output_dir / cache_path.name
            shutil.copy2(cache_path, saved_path)
            items.append({"imagePath": str(image_path), "cachePath": str(cache_path), "savedPath": str(saved_path)})
        except Exception as exc:
            items.append({"imagePath": raw_image_path, "error": str(exc)})
    return items


def _pred_cache_dir(pipeline_name: str) -> Path:
    return PRED_CACHE_ROOT / pipeline_name / "pred"


def _remove_cache_directory(target: Path, *, allow_pred_root: bool = False) -> None:
    resolved_target = target.resolve(strict=False)
    pred_cache_root = PRED_CACHE_ROOT.resolve(strict=False)
    datasets_root = DATASETS_ROOT.resolve(strict=False)

    is_pred_root = resolved_target == pred_cache_root and allow_pred_root
    is_pred_pipeline_cache = (
        pred_cache_root in resolved_target.parents
        and resolved_target.name == "pred"
        and resolved_target.parent.parent == pred_cache_root
    )
    is_gt_cache = (
        datasets_root in resolved_target.parents
        and resolved_target.name == "GT"
        and resolved_target.parent.name == ".cache"
    )
    if not (is_pred_root or is_pred_pipeline_cache or is_gt_cache):
        raise RuntimeError(f"Refusing to remove non-cache directory: {resolved_target}")
    shutil.rmtree(resolved_target, ignore_errors=True)


def _pred_cache_path(pipeline_name: str, image_path: str | Path) -> Path:
    output = _pred_cache_dir(pipeline_name) / _visualization_filename(Path(image_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def _visualization_filename(image_path: Path) -> str:
    digest = hashlib.sha1(str(image_path.resolve(strict=False)).encode("utf-8")).hexdigest()[:10]
    return f"{image_path.stem}-{digest}.jpg"


def _normalize_detections(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict) and item.get("bbox")]
    if isinstance(parsed, dict) and parsed.get("bbox"):
        return [parsed]
    return []


def _plot_detections(
    image_path: str | Path,
    detections: list[dict[str, Any]],
    plot_fields: list[str],
    output_path: Path,
) -> None:
    import cv2
    from dsetkit.visualize.plot import Plotter

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Failed to read image: {image_path}")

    plotter = Plotter(image)
    for detection in detections:
        bbox = detection.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue
        class_id = detection.get("class_id")
        text_parts = []
        for field in plot_fields:
            value = detection.get(field)
            if _is_empty_plot_value(value):
                continue
            formatted = _format_plot_value(value)
            if formatted:
                text_parts.append(formatted)
        text = " | ".join(text_parts)
        if text:
            plotter.detection(
                bbox=list(map(float, bbox)),
                class_id=int(class_id) if class_id is not None else 0,
                text=text,
            )
        else:
            color_id = int(class_id) if class_id is not None else 0
            plotter.box(list(map(float, bbox)), plotter.random_color(color_id))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = plotter.get()
    if not cv2.imwrite(str(output_path), rendered):
        raise RuntimeError("Failed to write dsetkit visualization image")
    if not output_path.is_file():
        raise RuntimeError("dsetkit Plotter did not create the visualization image")


def _is_empty_plot_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def _format_plot_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _plot_label(image_path: Path, label_path: Path, fmt: str, names: list[str], output_path: Path) -> None:
    from dsetkit.visualize.plot import plot

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plot(image_path=image_path, label_path=label_path, fmt=fmt, names=names, save_path=output_path)
    if not output_path.is_file():
        raise RuntimeError("dsetkit did not create the GT visualization image")


def _resolve_dataset_directory(raw_path: str) -> Path:
    path = Path(raw_path).resolve(strict=False)
    if path != DATASETS_ROOT and DATASETS_ROOT not in path.parents:
        raise HTTPException(status_code=403, detail="GT labels must be inside the configured datasets root")
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="GT label directory does not exist")
    return path


def _resolve_dataset_file(raw_path: str) -> Path:
    path = Path(raw_path).resolve(strict=False)
    if DATASETS_ROOT not in path.parents:
        raise HTTPException(status_code=403, detail="GT images must be inside the configured datasets root")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image does not exist")
    return path
