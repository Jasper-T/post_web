from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Literal

from backend.pipeline_core.api_pipeline.factory import ResponseParserConfig, create_request_pipeline
from backend.pipeline_core.api_pipeline.transport import TransportKind
from backend.pipeline_core.protocols.mappers import load_response_rules


CODE_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.getenv("WEB_POST_DATA_ROOT", CODE_ROOT / "data")).resolve()
PROJECT_ROOT = DATA_ROOT
TEMPLATES_DIR = DATA_ROOT / "templates"
PIPELINE_CONFIG_NAME = "pipeline.json"
RESERVED_TEMPLATE_DIR_NAMES = {"requests", "responses", "__pycache__"}
UNGROUPED_GROUP_NAME = "Ungrouped"
DELETED_GROUP_NAME = "Deleted"
PIPELINE_NAME_PATTERN = r"^[a-z][a-z0-9_-]{2,63}$"
SYSTEM_GROUP_NAMES = {UNGROUPED_GROUP_NAME, DELETED_GROUP_NAME}
PIPELINE_ASSET_FILES = {
    "header": "header.json",
    "body": "body.json",
    "response": "response.json",
    "mapping": "mapping.json",
    "post_config": "post_config.json",
}


@dataclass(slots=True)
class PipelineDefinition:
    name: str
    display_name: str
    group_name: str | None = None
    url: str = ""
    transport: TransportKind = "http"
    method: Literal["POST", "GET", "PUT", "PATCH", "DELETE"] = "POST"
    image_directory: str | None = None
    default_inputs: dict[str, Any] | None = None
    response_config: ResponseParserConfig | None = None
    connect_timeout: float = 3
    read_timeout: float = 30
    storage_kind: Literal["grouped"] = "grouped"
    storage_path: str | None = None


def get_pipeline_names() -> dict[str, PipelineDefinition]:
    definitions: dict[str, PipelineDefinition] = {}

    for definition in _iter_grouped_pipeline_definitions():
        definitions[definition.name] = definition


    return definitions


def get_pipeline_groups() -> list[str]:
    discovered: set[str] = {UNGROUPED_GROUP_NAME, DELETED_GROUP_NAME}
    if TEMPLATES_DIR.exists():
        for group_dir in sorted(TEMPLATES_DIR.iterdir()):
            if group_dir.is_dir() and group_dir.name not in RESERVED_TEMPLATE_DIR_NAMES:
                discovered.add(group_dir.name)

    for definition in get_pipeline_names().values():
        if definition.group_name and definition.group_name.strip():
            discovered.add(definition.group_name.strip())

    ordered = sorted(discovered - SYSTEM_GROUP_NAMES)
    return [UNGROUPED_GROUP_NAME, *ordered, DELETED_GROUP_NAME]


def get_pipeline_names_list() -> list[str]:
    return sorted(get_pipeline_names().keys())


def get_pipeline_definition(name: str) -> PipelineDefinition:
    definitions = get_pipeline_names()
    if name not in definitions:
        raise KeyError(f"Unknown pipeline: {name}")
    return definitions[name]


def get_pipeline_display_name(name: str) -> str:
    definition = get_pipeline_definition(name)
    return definition.display_name


def get_pipeline_response_names(name: str) -> list[str]:
    definition = get_pipeline_definition(name)
    response_config = definition.response_config
    if response_config is None:
        return [definition.display_name]

    rules = _load_definition_response_rules(definition)
    names = rules.get("names")
    if names is None:
        return [definition.display_name]
    if isinstance(names, list):
        return names

    ordered = sorted(((int(key), value) for key, value in names.items()), key=lambda item: item[0])
    return [value for _, value in ordered]


def build_pipeline_bundle(name: str, storage_dir: str | Path | None = None):
    definition = get_pipeline_definition(name)
    storage = "json" if storage_dir is not None else None
    storage_kwargs = {"save_dir": str(storage_dir)} if storage_dir is not None else None
    asset_paths = get_pipeline_asset_paths(definition, existing_only=True)

    return create_request_pipeline(
        display_name=definition.display_name,
        url=_resolve_pipeline_url(definition.url),
        transport=definition.transport,
        header_json=asset_paths.get("header"),
        body_json=asset_paths.get("body"),
        response_config=definition.response_config or _raise_missing_response_config(name),
        method=definition.method,
        connect_timeout=definition.connect_timeout,
        read_timeout=definition.read_timeout,
        storage=storage,
        storage_kwargs=storage_kwargs,
        default_inputs=definition.default_inputs,
        post_config=_load_optional_json_mapping(asset_paths.get("post_config")),
    )


def build_pipeline(name: str, storage_dir: str | Path | None = None):
    return build_pipeline_bundle(name, storage_dir=storage_dir)


def save_pipeline_definition(
    *,
    name: str,
    display_name: str,
    group_name: str | None = None,
    url: str,
    transport: TransportKind = "http",
    method: Literal["POST", "GET", "PUT", "PATCH", "DELETE"] = "POST",
    image_directory: str | None = None,
    default_inputs: dict[str, Any] | None = None,
    response_config: ResponseParserConfig | None = None,
    connect_timeout: float = 3,
    read_timeout: float = 30,
    overwrite: bool = False,
) -> Path:
    normalized_group = normalize_group_name(group_name)
    output_dir = get_group_pipeline_dir(normalized_group, name)
    output_path = output_dir / PIPELINE_CONFIG_NAME

    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Pipeline definition already exists: {output_path}")

    existing = get_pipeline_names().get(name)
    if existing is not None and overwrite:
        existing_path = Path(existing.storage_path) if existing.storage_path else None
        if existing.storage_kind == "grouped" and existing_path is not None and existing_path != output_dir:
            existing_path.parent.mkdir(parents=True, exist_ok=True)
            output_dir.parent.mkdir(parents=True, exist_ok=True)
            if output_dir.exists():
                shutil.rmtree(output_dir)
            shutil.move(str(existing_path), str(output_dir))

    output_dir.mkdir(parents=True, exist_ok=True)
    create_pipeline_group(normalized_group)

    payload = {
        "name": name,
        "display_name": display_name,
        "group_name": normalized_group,
        "url": url,
        "transport": transport,
        "method": method,
        "image_directory": image_directory,
        "default_inputs": default_inputs,
        "connect_timeout": connect_timeout,
        "read_timeout": read_timeout,
    }
    if response_config is not None:
        payload["response_parser"] = {
            "rule_json": response_config.rule_json,
        }

    _write_json_atomic(output_path, payload)

    return output_path


def load_pipeline_definition(path: str | Path) -> PipelineDefinition:
    raw_path = Path(path)
    definition_path = raw_path / PIPELINE_CONFIG_NAME if raw_path.is_dir() else raw_path
    with definition_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    response_config = _load_response_config(raw, definition_path)
    storage_kind = "grouped"
    storage_root = definition_path.parent

    return PipelineDefinition(
        name=raw["name"],
        display_name=raw.get("display_name", raw["name"]),
        group_name=raw.get("group_name"),
        url=raw["url"],
        transport=raw.get("transport", "http"),
        method=raw.get("method", "POST"),
        image_directory=raw.get("image_directory"),
        default_inputs=raw.get("default_inputs"),
        response_config=response_config,
        connect_timeout=raw.get("connect_timeout", 3),
        read_timeout=raw.get("read_timeout", 30),
        storage_kind=storage_kind,
        storage_path=str(storage_root),
    )


def normalize_group_name(name: str | None) -> str:
    normalized = (name or "").strip()
    return normalized or UNGROUPED_GROUP_NAME


def get_group_pipeline_dir(group_name: str | None, pipeline_name: str) -> Path:
    return TEMPLATES_DIR / normalize_group_name(group_name) / pipeline_name



def create_pipeline_group(name: str) -> list[str]:
    normalized = normalize_group_name(name)
    validate_group_name(normalized)
    (TEMPLATES_DIR / normalized).mkdir(parents=True, exist_ok=True)
    return get_pipeline_groups()


def delete_pipeline_group(name: str) -> list[str]:
    normalized = normalize_group_name(name)
    group_dir = TEMPLATES_DIR / normalized
    if group_dir.exists():
        shutil.rmtree(group_dir)
    return get_pipeline_groups()


def rename_pipeline_group(name: str, next_name: str) -> list[str]:
    current_name = normalize_group_name(name)
    target_name = normalize_group_name(next_name)
    validate_group_name(target_name)
    if current_name == DELETED_GROUP_NAME:
        raise ValueError("Deleted group cannot be renamed")
    if current_name == target_name:
        return get_pipeline_groups()

    current_dir = TEMPLATES_DIR / current_name
    target_dir = TEMPLATES_DIR / target_name
    if target_dir.exists():
        raise FileExistsError(f"Group already exists: {target_name}")

    if not current_dir.exists() and current_name not in get_pipeline_groups():
        raise FileNotFoundError(f"Group not found: {current_name}")

    if current_dir.exists():
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(current_dir), str(target_dir))
    else:
        target_dir.mkdir(parents=True, exist_ok=True)

    for pipeline_dir in sorted(target_dir.iterdir()):
        if not pipeline_dir.is_dir():
            continue
        config_path = pipeline_dir / PIPELINE_CONFIG_NAME
        if not config_path.exists():
            continue
        with config_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        payload["group_name"] = target_name
        _sync_response_rule_path(payload, target_name, pipeline_dir.name)
        _write_json_atomic(config_path, payload)

    return get_pipeline_groups()


def validate_group_name(name: str) -> None:
    normalized = normalize_group_name(name)
    if normalized in SYSTEM_GROUP_NAMES:
        return
    if not re.fullmatch(PIPELINE_NAME_PATTERN, normalized):
        raise ValueError(
            "Group name must start with a lowercase letter, be 3-64 characters, "
            "and only use lowercase letters, numbers, _ and -"
        )
    if normalized[-1] in {"_", "-"} or "__" in normalized or "--" in normalized or "_-" in normalized or "-_" in normalized:
        raise ValueError("Group name cannot end with or repeat separators")


def _sync_response_rule_path(payload: dict[str, Any], group_name: str, pipeline_name: str) -> None:
    pipeline_dir = get_group_pipeline_dir(group_name, pipeline_name)
    parser = payload.get("response_parser")
    if isinstance(parser, dict):
        rule_json = parser.get("rule_json")
        if isinstance(rule_json, str) and rule_json:
            parser["rule_json"] = _replace_template_group_path(rule_json, group_name)
        elif (pipeline_dir / "rule.json").exists():
            parser["rule_json"] = _to_data_relative(pipeline_dir / "rule.json")


def _replace_template_group_path(value: str, group_name: str) -> str:
    normalized = value.replace("\\", "/")
    parts = normalized.split("/")
    if "templates" not in parts:
        return value
    template_index = parts.index("templates")
    suffix = parts[template_index + 1:]
    if len(suffix) < 2:
        return value
    return "/".join(["templates", group_name, *suffix[1:]])


def update_pipeline_definition_assets(
    name: str,
    *,
    connect_timeout: float | None = None,
    read_timeout: float | None = None,
    response_rule_json: str | None = None,
) -> None:
    definition = get_pipeline_definition(name)
    if definition.storage_kind != "grouped" or not definition.storage_path:
        return

    config_path = Path(definition.storage_path) / PIPELINE_CONFIG_NAME
    with config_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if connect_timeout is not None:
        payload["connect_timeout"] = connect_timeout
    if read_timeout is not None:
        payload["read_timeout"] = read_timeout
    if response_rule_json is not None:
        response_parser = payload.get("response_parser")
        if not isinstance(response_parser, dict):
            response_parser = {}
            payload["response_parser"] = response_parser
        response_parser["rule_json"] = response_rule_json
    _write_json_atomic(config_path, payload)


def update_pipeline_definition_group(name: str, group_name: str | None) -> None:
    definition = get_pipeline_definition(name)
    normalized_group = normalize_group_name(group_name)
    create_pipeline_group(normalized_group)
    if definition.storage_kind == "grouped" and definition.storage_path:
        current_dir = Path(definition.storage_path)
        next_dir = get_group_pipeline_dir(normalized_group, name)
        if current_dir != next_dir:
            next_dir.parent.mkdir(parents=True, exist_ok=True)
            if next_dir.exists():
                shutil.rmtree(next_dir)
            shutil.move(str(current_dir), str(next_dir))
        config_path = next_dir / PIPELINE_CONFIG_NAME
        with config_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        payload["group_name"] = normalized_group
        _sync_response_rule_path(payload, normalized_group, name)
        _write_json_atomic(config_path, payload)
        _cleanup_empty_group_dir(current_dir.parent)
        return


def get_pipeline_asset_path(definition: PipelineDefinition, asset_name: str, *, existing_only: bool = False) -> str | None:
    file_name = PIPELINE_ASSET_FILES.get(asset_name)
    if file_name is None or not definition.storage_path:
        return None
    path = Path(definition.storage_path) / file_name
    if existing_only and not path.exists():
        return None
    return str(path)


def get_pipeline_asset_relative_path(definition: PipelineDefinition, asset_name: str, *, existing_only: bool = False) -> str | None:
    raw_path = get_pipeline_asset_path(definition, asset_name, existing_only=existing_only)
    if raw_path is None:
        return None
    return _to_project_relative(Path(raw_path))


def get_pipeline_asset_paths(definition: PipelineDefinition, *, existing_only: bool = False) -> dict[str, str | None]:
    return {
        asset_name: get_pipeline_asset_path(definition, asset_name, existing_only=existing_only)
        for asset_name in PIPELINE_ASSET_FILES
    }


def get_pipeline_asset_relative_paths(definition: PipelineDefinition, *, existing_only: bool = False) -> dict[str, str | None]:
    return {
        asset_name: get_pipeline_asset_relative_path(definition, asset_name, existing_only=existing_only)
        for asset_name in PIPELINE_ASSET_FILES
    }

def move_pipeline_to_deleted_group(name: str) -> None:
    definition = get_pipeline_definition(name)
    target_name = ensure_unique_pipeline_name(DELETED_GROUP_NAME, definition.name)
    if target_name != definition.name:
        rename_pipeline_definition(definition.name, target_name)
    update_pipeline_definition_group(target_name, DELETED_GROUP_NAME)


def reassign_group_members(group_name: str, next_group_name: str | None = None) -> None:
    normalized = normalize_group_name(group_name)
    target = normalize_group_name(next_group_name or DELETED_GROUP_NAME)
    for definition in get_pipeline_names().values():
        if normalize_group_name(definition.group_name) == normalized:
            update_pipeline_definition_group(definition.name, target)


def rename_pipeline_definition(name: str, next_name: str) -> str:
    definition = get_pipeline_definition(name)
    current_name = definition.name
    target_name = next_name.strip()
    if current_name == target_name:
        return current_name
    if target_name in get_pipeline_names():
        raise FileExistsError(f"Pipeline already exists: {target_name}")

    if definition.storage_kind == "grouped" and definition.storage_path:
        current_dir = Path(definition.storage_path)
        target_dir = current_dir.parent / target_name
        if target_dir.exists():
            raise FileExistsError(f"Pipeline storage already exists: {target_dir}")
        shutil.move(str(current_dir), str(target_dir))
        config_path = target_dir / PIPELINE_CONFIG_NAME
        with config_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        payload["name"] = target_name
        _write_json_atomic(config_path, payload)
        return target_name

    raise FileNotFoundError(f"Pipeline storage not found for: {current_name}")


def ensure_unique_pipeline_name(group_name: str | None, pipeline_name: str) -> str:
    normalized_group = normalize_group_name(group_name)
    candidate = pipeline_name.strip()
    suffix = 1
    existing_names = set(get_pipeline_names())

    while candidate in existing_names or get_group_pipeline_dir(normalized_group, candidate).exists():
        candidate = f"{pipeline_name}_{suffix}"
        suffix += 1

    return candidate


def remove_pipeline_definition(name: str) -> None:
    definition = get_pipeline_definition(name)
    if normalize_group_name(definition.group_name) != DELETED_GROUP_NAME:
        raise ValueError("Only pipelines in Deleted can be permanently removed")

    if definition.storage_kind == "grouped" and definition.storage_path:
        pipeline_dir = Path(definition.storage_path)
        if pipeline_dir.exists():
            shutil.rmtree(pipeline_dir)
            _cleanup_empty_group_dir(pipeline_dir.parent)
        return

    raise FileNotFoundError(f"Pipeline storage not found for: {name}")


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _iter_grouped_pipeline_definitions() -> list[PipelineDefinition]:
    definitions: list[PipelineDefinition] = []
    if not TEMPLATES_DIR.exists():
        return definitions

    for group_dir in sorted(TEMPLATES_DIR.iterdir()):
        if not group_dir.is_dir():
            continue
        if group_dir.name in RESERVED_TEMPLATE_DIR_NAMES:
            continue
        for pipeline_dir in sorted(group_dir.iterdir()):
            if not pipeline_dir.is_dir():
                continue
            config_path = pipeline_dir / PIPELINE_CONFIG_NAME
            if not config_path.exists():
                continue
            definition = load_pipeline_definition(pipeline_dir)
            if not definition.group_name:
                definition.group_name = group_dir.name
            definitions.append(definition)
    return definitions


def _cleanup_empty_group_dir(path: Path) -> None:
    if path.name in RESERVED_TEMPLATE_DIR_NAMES:
        return
    if path.exists() and path.is_dir() and not any(path.iterdir()):
        path.rmdir()


def _copy_optional_project_file(source: str | None, target: Path) -> Path | None:
    if not source:
        return None
    source_path = Path(source)
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source
    if not source_path.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target)
    return target


def _to_data_relative(path: Path) -> str:
    return path.resolve().relative_to(DATA_ROOT).as_posix()


def _to_project_relative(path: Path) -> str:
    return _to_data_relative(path)


def _resolve_pipeline_url(value: str) -> str:
    base_url = os.getenv("WEB_POST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return value.replace("${WEB_POST_BASE_URL}", base_url).replace("{WEB_POST_BASE_URL}", base_url)


def _resolve_optional_file(value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / value
    return str(path)


def _load_optional_json_mapping(path_value: str | None) -> dict[str, Any] | None:
    resolved = _resolve_optional_file(path_value)
    if resolved is None:
        return None
    path = Path(resolved)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else None


def _raise_missing_response_config(name: str) -> ResponseParserConfig:
    raise ValueError(f"Pipeline `{name}` is missing response_parser config")


def _load_response_config(raw: dict[str, Any], definition_path: Path) -> ResponseParserConfig | None:
    response_parser = raw.get("response_parser")
    if response_parser is None:
        return None
    if not isinstance(response_parser, dict):
        raise ValueError(f"Invalid response_parser in {definition_path}: expected object")
    rule_json = response_parser.get("rule_json")
    if not isinstance(rule_json, str) or not rule_json:
        raise ValueError(f"Invalid response_parser.rule_json in {definition_path}: expected non-empty string")

    template_input = response_parser.get("template_input")
    template_input_json = response_parser.get("template_input_json")
    if template_input_json is not None and not isinstance(template_input_json, str):
        raise ValueError(
            f"Invalid response_parser.template_input_json in {definition_path}: expected string"
        )
    if isinstance(template_input, dict):
        pass
    else:
        template_input = None
    if template_input_json:
        template_input = _load_optional_json_mapping(template_input_json) or template_input

    return ResponseParserConfig(
        rule_json=_resolve_optional_file(rule_json),
        template_input=template_input,
    )


def _load_definition_response_rules(definition: PipelineDefinition) -> dict[str, Any]:
    response_config = definition.response_config
    if response_config is None:
        return {}
    if response_config.rules is not None:
        return load_response_rules(response_config.rules)
    if response_config.rule_json is not None:
        return load_response_rules(response_config.rule_json)
    return {}

