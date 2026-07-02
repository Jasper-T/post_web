import cv2
import json
from pathlib import Path

from dsetkit.visualize.plot import Plotter
from dsetkit.utils.image import get_image_paths


def load_detections(image_path: Path, det_dir: Path) -> list[dict]:
    image_name = image_path.stem
    json_path = det_dir / f"{image_name}.json"

    if not json_path.exists():
        return []

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def draw_detections(image_path, detections:list[dict], names:list[str], output_dir):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"failed to read image: {image_path}")

    pen = Plotter(img)
    for det in detections:
        bbox = det.get('bbox')
        conf = det.get('conf')
        label = det.get('label')
        extra_text = det.get('license_number', None)
        
        if label is None:
            class_id = det.get('class_id')
            label = names[class_id]
        else:
            class_id = names.index(label)
        plot_text = f"{label}_{extra_text}" if extra_text else label
        pen.detection(bbox, class_id, plot_text, conf)

    image_path = Path(image_path).resolve()
    image_name = image_path.name

    pen.save(Path(output_dir) / image_name)

    return pen.image

def draw_ocr(image_path, detections:list[dict], names:list[str], output_dir):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"failed to read image: {image_path}")

    pen = Plotter(img)
    for det in detections:
        bbox = det.get('bbox')
        text = det.get('number')
        pen.detection(bbox, 0, text)

    image_path = Path(image_path).resolve()
    image_name = image_path.name

    pen.save(Path(output_dir) / image_name)

    return pen.image

def run_single(image_path, names, det_dir, output_dir):
    image_path = Path(image_path)
    
    detections = load_detections(image_path, det_dir)
    if not detections:
        print(f"no detections found for image: {image_path}")
        return
    
    draw_detections(
        image_path=image_path,
        detections=detections,
        names=names,
        output_dir=output_dir
    )


def run(path, names, det_dir, output_dir,):
    path = Path(path)
    if not path.exists():
        raise ValueError(f"path does not exist: {path}")
    
    det_dir = Path(det_dir)
    if not det_dir.exists():
        raise ValueError(f"path does not exist: {path}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"output dir: {output_dir}")
    
    if path.is_dir():
        image_paths = get_image_paths(path)
        print(f"total images: {len(image_paths)}")
        
        for image_path in image_paths:
            run_single(image_path, names, det_dir, output_dir)
    
    elif path.is_file():
        run_single(path, names, det_dir, output_dir)
    else:
        raise ValueError(f"path is not a valid directory or file: {path}")

    print(f"finished")


if __name__ == "__main__":
    
    img_path = "/workspace/projects/00_datasets/smk/images/1773960001836.jpg"
    
    det_dir = "results/dets/f_welding"
    
    plot_dir = "results/plot"
    
    names = ["welding"]

    run(
        path = img_path, 
        names = names, 
        det_dir = det_dir,
        output_dir = plot_dir, 
    )


