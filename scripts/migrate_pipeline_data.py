from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


BUSINESS_FILE_NAMES = {
    "pipeline.json",
    "header.json",
    "body.json",
    "response.json",
    "mapping.json",
    "map.json",
    "post_config.json",
    "rule.json",
}


def rewrite_paths(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: rewrite_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rewrite_paths(item) for item in value]
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        if normalized.startswith("pipelines/templates/"):
            return normalized.removeprefix("pipelines/")
        if normalized.startswith("results/"):
            return normalized
    return value


def copy_json_tree(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    shutil.copytree(source, destination, dirs_exist_ok=True)
    for path in destination.rglob("*.json"):
        if path.name not in BUSINESS_FILE_NAMES:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        path.write_text(
            json.dumps(rewrite_paths(payload), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def migrate(project_root: Path, data_root: Path) -> None:
    data_root.mkdir(parents=True, exist_ok=True)
    source_templates = project_root / "pipelines" / "templates"
    copy_json_tree(source_templates, data_root / "templates")

    groups_source = source_templates / "groups.json"
    if groups_source.exists():
        shutil.copy2(groups_source, data_root / "groups.json")

    definitions_source = project_root / "pipelines" / "definitions"
    copy_json_tree(definitions_source, data_root / "definitions")

    for name in ("results", "logs"):
        source = project_root / name
        if source.exists():
            shutil.copytree(source, data_root / name, dirs_exist_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy business pipeline data outside the web code directory.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    migrate(args.project_root.resolve(), args.data_root.resolve())
    print(f"Pipeline data migrated to {args.data_root.resolve()}")
