import json
from pathlib import Path

from dsetkit.utils.image import get_image_paths, read_image_info
from dsetkit.annotations.schema import Annotation, AnnotationItem, BBox
from dsetkit.annotations.io import dump, auto_label_path


def load_detections(image_path: Path, det_dir: Path) -> list[dict]:
    image_name = image_path.stem
    json_path = det_dir / f"{image_name}.json"

    if not json_path.exists():
        return []

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def dump_detections(
    image_path:Path, 
    detections:list[dict], 
    names:list[str], 
    out_dir:Path, 
    target_format:str
):
    img_info = read_image_info(image_path)

    annotation = Annotation(
        width=img_info.width,
        height=img_info.height,
        items=[]
    )

    for det in detections:
        x1, y1, x2, y2 = det['bbox']

        label = det.get('label')
        
        if label is None:
            class_id = det.get('class_id')
            if class_id is None:
                raise ValueError(f"label and class_id are both None in det: {det}")
            label = names[class_id]
        else:
            if label not in names:
                raise ValueError(f"label not found in names: {label}")
            class_id = names.index(label)
        
        annotation_item = AnnotationItem(
            category=label,
            category_id=class_id,
            bbox=BBox(x1=x1, x2=x2, y1=y1, y2=y2),
            extra={'conf': det['conf']}
        )

        annotation.items.append(annotation_item)
    
    out_path = auto_label_path(
        image_path, 
        target_format,
        out_dir
    )

    dump(annotation, out_path, target_format)


def run_single(image_path, names, det_dir, output_dir, target_format):
    image_path = Path(image_path)
    
    detections = load_detections(image_path, det_dir)
    if not detections:
        print(f"no detections found for image: {image_path}")
        return
    
    dump_detections(
        image_path=image_path,
        detections=detections,
        names=names,
        out_dir=output_dir,
        target_format=target_format
    )


def run(path, names, det_dir, output_dir="results", target_format="labelme"):
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
            run_single(image_path, names, det_dir, output_dir, target_format)
    
    elif path.is_file():
        run_single(path, names, det_dir, output_dir, target_format)

    print(f"finished")


if __name__ == "__main__":
    #--------------------------------------------------------------------------------
    # 标签自动保存路径示意: 
    #     输入不管是图片或者文件夹:   /path/to/images/image.jpg 或 /path/to/images
    #     标签都会保存到: /path/to/labelme 或 /path/to/labels 或 /path/to/xmls
   
    # 标签的输出格式, 支持: 'yolo'(txt), 'voc'(xml), 'labelme'(json)
    # --------------------------------------------------------------------------------
    from dsetkit.annotations.io import FORMAT_DIRS
    target_format = "labelme"  

    img_path = "/workspace/projects/00_datasets/smk/images"  # 图片路径, 支持: 单个图片路径, 或 图片目录路径
    
    det_dir = "results/dets/x_smoke"  # 检测结果目录
    
    out_dir = f"results/x_smoke/"  # 转换的标注标签输出路径
    
    names = ["smoking"]  # 检测类别名称列表

    run(
        path = img_path, 
        names = names, 
        det_dir = det_dir,
        output_dir = out_dir,
        target_format = target_format
    )