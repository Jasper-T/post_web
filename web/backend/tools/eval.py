import json
from pathlib import Path

from dsetkit.dataset import Dataset
from dsetkit.evaluator import  Evaluator
from dsetkit.annotations.io import FORMAT_DIRS


class MyEvaluator(Evaluator):
    def _load_predictions(self, image_path):
        image_name = Path(image_path).stem
        json_path = DET_DIR / f"{image_name}.json"

        if not json_path.exists():
            return []

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data


def run(
    dataset_dir, 
    names, 
    input_format,
    conf_threshold,
    iou_threshold
    ):

    dataset_dir = Path(dataset_dir)
    if not dataset_dir.is_dir():
        raise ValueError(f"dataset_dir is not a valid directory: {dataset_dir}")

    im_dir = dataset_dir / "images"

    lb_dir = dataset_dir / FORMAT_DIRS[input_format]
    
    dataset = Dataset(
        image_dir=im_dir,
        label_dir=lb_dir,
        names=names,
        input_format=input_format
    )

    evaluator = MyEvaluator(
        dataset=dataset
    )

    metrics = evaluator.evaluate(conf_threshold=conf_threshold, iou_threshold=iou_threshold, print_metrics=True)

    print()
    print(metrics)


if __name__ == "__main__":
    #--------------------------------------------------------------------------------
    # 数据集目录: 
    #    目录下必须包含图片文件夹和标签文件夹
    #    图片文件夹必须是: images
    #    标签文件夹必须是: labelme, xmls, labels
    # input_format 支持: 'labelme', 'voc', 'yolo' 
    # 分别对应的标签文件夹名称必须为：labelme, xmls, labels
    # --------------------------------------------------------------------------------

    # dataset_dir = "/workspace/projects/00_datasets/people"  # 数据集目录
    dataset_dir = "./results"  # 数据集目录

    DET_DIR = Path("./results/dets/x_smoke")  # 检测结果目录

    names = ["smoking"]  # 检测类别名称列表
    
    input_format = "voc"  # 输入 ground truth 标签的格式

    conf_threshold = 0.5
    iou_threshold = 0.2
    
    run(
        dataset_dir = dataset_dir, 
        names = names, 
        input_format = input_format,
        conf_threshold = conf_threshold,
        iou_threshold = iou_threshold
    )