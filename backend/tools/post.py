from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.pipeline_core.api_pipeline import ResponseParserConfig
from backend.pipeline_core import (
    build_pipeline as build_registered_pipeline,
    get_pipeline_names,
    get_pipeline_names_list,
    save_pipeline_definition,
)


from backend.pipeline_core.registry import DATA_ROOT


PROJECT_ROOT = DATA_ROOT


def build_pipeline(algorithm_name: str, save_dir: str | Path | None):
    return build_registered_pipeline(name=algorithm_name, storage_dir=save_dir)


def run(algorithm_name, path, save_dir, **kwargs):
    path = Path(path)
    if not path.exists():
        raise ValueError(f"path does not exist: {path}")

    if algorithm_name not in get_pipeline_names():
        raise ValueError(f"unsupported algorithm_name: {algorithm_name}")

    save_dir = Path(save_dir) / algorithm_name
    print(f"save dir: {save_dir}")

    pipeline = build_pipeline(algorithm_name, save_dir)

    results = {}
    if path.is_dir():
        image_utils = _import_image_utils()
        get_image_paths = getattr(image_utils, "get_image_paths")
        image_paths = get_image_paths(path)
        print(f"total images: {len(image_paths)}")
        for image_path in image_paths:
            try:
                result = pipeline.run(
                    inputs=image_path,
                    save=True,
                    save_name=Path(image_path).stem,
                    **kwargs,
                )
                results[image_path] = result
            except Exception as exc:
                print(f"{path} run_post failed: {exc}")

    elif path.is_file():
        result = pipeline.run(
            inputs=path,
            save=True,
            save_name=path.stem,
            **kwargs,
        )
        results[path] = result
    return results


def create_pipeline(
    *,
    name: str,
    display_name: str,
    url: str,
    header_json: str | Path,
    body_json: str | Path,
    response_rule_json: str | Path,
    default_inputs: dict[str, Any] | None = None,
    template_input: dict[str, Any] | None = None,
    transport: str = "http",
    method: str = "POST",
    connect_timeout: float = 3,
    read_timeout: float = 30,
    overwrite: bool = False,
) -> Path:
    definition_path = save_pipeline_definition(
        name=name,
        display_name=display_name,
        url=url,
        transport=transport,
        method=method,
        header_json=_to_project_relative_path(header_json),
        body_json=_to_project_relative_path(body_json),
        response_config=ResponseParserConfig(
            rule_json=_to_project_relative_path(response_rule_json),
            template_input=template_input,
        ),
        default_inputs=default_inputs,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        overwrite=overwrite,
    )
    return definition_path


def list_algorithms():
    print("\nsupported algorithms:")
    for algorithm_name in get_pipeline_names_list():
        print(f"- {algorithm_name}")


def main():
    parser = argparse.ArgumentParser(description="Pipeline helper for create/run in web-post")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List registered pipelines")
    list_parser.set_defaults(handler=_handle_list)

    create_parser = subparsers.add_parser("create", help="Create or update a pipeline definition")
    create_parser.add_argument("--name", required=True, help="Pipeline name")
    create_parser.add_argument("--display-name", required=True, help="Pipeline display name")
    create_parser.add_argument("--url", required=True, help="Request URL")
    create_parser.add_argument("--header-json", required=True, help="Header JSON file path")
    create_parser.add_argument("--body-json", required=True, help="Body JSON file path")
    create_parser.add_argument("--response-rule-json", required=True, help="Response rule JSON file path")
    create_parser.add_argument("--default-inputs-json", help="Optional JSON file or inline JSON for default_inputs")
    create_parser.add_argument("--template-input-json", help="Optional JSON file or inline JSON for response sample")
    create_parser.add_argument("--transport", default="http", help="Transport kind")
    create_parser.add_argument("--method", default="POST", help="HTTP method")
    create_parser.add_argument("--connect-timeout", type=float, default=3)
    create_parser.add_argument("--read-timeout", type=float, default=30)
    create_parser.add_argument("--overwrite", action="store_true")
    create_parser.set_defaults(handler=_handle_create)

    run_parser = subparsers.add_parser("run", help="Run a registered pipeline")
    run_parser.add_argument("--name", required=True, help="Pipeline name")
    run_parser.add_argument("--path", required=True, help="Image path or directory")
    run_parser.add_argument("--save-dir", default="results/dets", help="Detection output directory")
    run_parser.add_argument("--extra-json", help="Optional JSON file or inline JSON merged into RequestInput.extra")
    run_parser.set_defaults(handler=_handle_run)

    args = parser.parse_args()
    args.handler(args)


def _handle_list(_args) -> None:
    list_algorithms()


def _handle_create(args) -> None:
    default_inputs = _load_optional_json(args.default_inputs_json)
    template_input = _load_optional_json(args.template_input_json)

    definition_path = create_pipeline(
        name=args.name,
        display_name=args.display_name,
        url=args.url,
        header_json=args.header_json,
        body_json=args.body_json,
        response_rule_json=args.response_rule_json,
        default_inputs=default_inputs,
        template_input=template_input,
        transport=args.transport,
        method=args.method,
        connect_timeout=args.connect_timeout,
        read_timeout=args.read_timeout,
        overwrite=args.overwrite,
    )
    print(f"pipeline definition saved: {definition_path}")


def _handle_run(args) -> None:
    extra = _load_optional_json(args.extra_json) or {}
    results = run(
        algorithm_name=args.name,
        path=args.path,
        save_dir=args.save_dir,
        **extra,
    )
    print(f"processed items: {len(results)}")


def _load_optional_json(raw_value: str | None) -> dict[str, Any] | None:
    if not raw_value:
        return None

    source_path = Path(raw_value)
    if source_path.exists():
        with source_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    value = json.loads(raw_value)
    if not isinstance(value, dict):
        raise TypeError("JSON input must be an object")
    return value


def _to_project_relative_path(value: str | Path) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    else:
        path = path.resolve()
    return path.relative_to(PROJECT_ROOT).as_posix()


def _import_image_utils():
    try:
        from dsetkit.utils import image as image_utils
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "dsetkit.utils.image is required for directory run mode, but is not available in the current environment"
        ) from exc
    return image_utils


if __name__ == "__main__":
    main()

