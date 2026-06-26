import cv2
from pathlib import Path

from dsetkit.dataset import Dataset
from dsetkit.annotations.io import FORMAT_DIRS, load
from dsetkit.visualize.plot import Plotter


def draw_anno(dataset:Dataset, input_format:str, anno_dir:Path):
    names = dataset.names

    for sample in dataset.samples:
        image_path = sample.image_path
        label_path = sample.label_path

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"failed to read image: {image_path}")

        ann = load(
            image_path=image_path,
            label_path=label_path,
            fmt=input_format,
            names = names
        )

        pen = Plotter(img)
        for item in ann.items:
            pen.detection_from_schema(item)
        
        pen.save(anno_dir / Path(image_path).name)
        
        return pen.image


def run(dataset_dir, names, input_format, anno_dir):
    dataset_dir = Path(dataset_dir)
    if not dataset_dir.is_dir():
        raise ValueError(f"dataset_dir is not a valid directory: {dataset_dir}")

    im_dir = dataset_dir / "images"
    lb_dir = dataset_dir / FORMAT_DIRS[input_format]
    anno_dir = dataset_dir / "annos"
    anno_dir.mkdir(parents=True, exist_ok=True)

    dataset = Dataset(
        image_dir=im_dir,
        label_dir=lb_dir,
        names=names,
        input_format=input_format
    )  
    
    draw_anno(dataset, input_format, anno_dir)


if __name__ == "__main__":

    dataset_dir = "results/x_smoke"

    names = ["smoking"]

    input_format = "voc"
    
    anno_dir = "results/annos"

    run(dataset_dir, names, input_format, anno_dir)

