from math import e
from pathlib import Path

from backend.tools.post import run as run_post
from backend.tools.plot import draw_detections, draw_ocr
from backend.tools.dump import dump_detections


def run(
    algorithm_name, 
    path, 
    names, 
    det_dir, 
    plot_dir=None,
    dump_dir=None,
    target_format="labelme",
    **kwargs
    ):
    
    results = run_post(
        algorithm_name=algorithm_name, 
        path=path, 
        save_dir=det_dir,
        **kwargs
    )

    if not isinstance(results, dict):
        raise TypeError(f"unexpected results type from post.run: {type(results).__name__}")
    
    if plot_dir is not None:
        plot_dir = Path(plot_dir) / algorithm_name
        plot_dir.mkdir(parents=True, exist_ok=True)
        for image_path, detections in results.items():
            if not detections:
                continue
            # draw_detections(
            draw_ocr(
                image_path=image_path, 
                detections=detections, 
                names=names, 
                output_dir=plot_dir
            )
    
    if dump_dir is not None and target_format is not None and (target_format in ['labelme', 'voc', 'yolo']):
        dump_dir = Path(dump_dir) / algorithm_name
        dump_dir.mkdir(parents=True, exist_ok=True)
        for image_path, detections in results.items():
            if not detections:
                continue
            dump_detections(
                image_path=image_path, 
                detections=detections, 
                names=names, 
                out_dir=dump_dir, 
                target_format=target_format
            )


def list_algorithms():
    from backend.pipeline_core import get_pipeline_names_list
    print("\nsupported algorithms:")
    for algorithm_name in get_pipeline_names_list():
        print(f"- {algorithm_name}")


def main():
    list_algorithms()          # 目前支持的算法名称

    algorithm_name = "f_ebike_licecse" # 算法名称，x开头为星河平台，f开头为扶摇平台
    
    input_path = "/workspace/projects/00_datasets/license/13.jpg"  # 支持单图路径或目录路径

    det_dir  = "results/dets"  # 保存检测结果目录
    
    names = ['motorbike']        # 检测类别名称列表
    plot_dir = "results/plot"  # 保存标注图片目录
    target_format = "labelme"  # 标签格式，必须为 'yolo', 'voc', 'labelme' 之一
    dump_dir = "results/dump"  # 保存标注标签目录
    
    # plot_dir 为 None 时，不触发 plot 的功能
    # dump_dir 为 None 时，不触发 dump 的功能
    # target_format 为 None 时，不触发 dump 的功能

    run(
        algorithm_name = algorithm_name, 
        path = input_path, 
        names = names, 
        det_dir = det_dir, 
        plot_dir = plot_dir,
        # dump_dir = dump_dir,
        target_format=target_format,
        # person_count_threshold = 3
    )


if __name__ == "__main__":
    main()

    
