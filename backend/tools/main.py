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
    list_algorithms()

    algorithm_name = "f_ebike_licecse"
    
    input_path = "/workspace/projects/00_datasets/license/13.jpg"

    det_dir  = "results/dets"
    
    names = ['motorbike']
    plot_dir = "results/plot"
    target_format = "labelme"
    dump_dir = "results/dump"
    




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

    
