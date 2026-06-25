from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any


_MISSING = object()


class ResponseParseError(ValueError):
    pass


class ResponseMapper(ABC):
    @abstractmethod
    def map(self, response_json: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any] | None:
        raise NotImplementedError


class RuleBasedResponseMapper(ResponseMapper):
    TEMPLATE_DIR = Path(os.getenv("FUXING_DATA_ROOT", Path(__file__).resolve().parents[4] / "data")) / "templates" / "responses"

    def __init__(self, rule_name: str | None = None, rules: dict[str, Any] | None = None):
        if rule_name is None and rules is None:
            raise ValueError("rule_name or rules is required")

        self.rule_name = rule_name
        self.rules = deepcopy(rules) if rules is not None else self._load_rules(rule_name)

    def _load_rules(self, rule_name: str) -> dict[str, Any]:
        rule_path = self.TEMPLATE_DIR / rule_name
        with rule_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def map(self, response_json: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any] | None:
        if not isinstance(response_json, dict):
            raise ResponseParseError("response_json must be a dict")

        outputs = []
        for item in self.extract_items(response_json):
            outputs.append(self.build_output(item))
        return outputs

    def extract_items(self, response_json: dict[str, Any]) -> list[dict[str, Any]]:
        collection_paths = self.rules.get("collection_paths", [])
        item_path = self.rules.get("item_path")

        for collection_path in collection_paths:
            collection = self.get_path(response_json, collection_path)
            items = self.normalize_collection(collection, item_path)
            if items is not None:
                return items

        joined_paths = ", ".join(collection_paths) if collection_paths else "<empty>"
        raise ResponseParseError(f"failed to locate collection paths: {joined_paths}")

    def normalize_collection(self, collection: Any, item_path: str | None) -> list[dict[str, Any]] | None:
        if not isinstance(collection, list):
            return None

        if item_path is None:
            return collection

        flattened = []
        for item in collection:
            nested_items = self.get_path(item, item_path)
            if isinstance(nested_items, list):
                flattened.extend(nested_items)

        return flattened

    def get_path(self, data: Any, path: str | None, default: Any = _MISSING) -> Any:
        if path is None or path == "":
            return data

        current = data
        for part in path.split("."):
            if not isinstance(current, dict):
                return default
            if part not in current:
                return default
            current = current[part]
        return current

    def apply_cast(self, value: Any, cast_name: str | None) -> Any:
        if cast_name is None or value is None:
            return value

        if cast_name == "int":
            return int(value)
        if cast_name == "float":
            return float(value)
        if cast_name == "str":
            return str(value)

        raise ValueError(f"unsupported cast: {cast_name}")

    def apply_map(self, value: Any, value_map: dict[str, Any]) -> Any:
        if value in value_map:
            return value_map[value]

        key = str(value)
        return value_map.get(key, value)

    def resolve_field(self, item: dict[str, Any], spec: dict[str, Any]) -> Any:
        if "literal" in spec:
            value = spec["literal"]
        else:
            if "extract" in spec:
                value = self.extract_value(item, spec["extract"])
            else:
                primary_path = spec.get("path")
                value = self.get_path(item, primary_path)

            if value is _MISSING:
                value = None

            if "map" in spec:
                value = self.apply_map(value, spec["map"])

            if value in (None, ""):
                for fallback_path in spec.get("fallback_paths", []):
                    fallback_value = self.get_path(item, fallback_path)
                    if fallback_value is not _MISSING and fallback_value not in (None, ""):
                        value = fallback_value
                        break

        if value in (None, "") and "default" in spec:
            value = spec["default"]

        return self.apply_cast(value, spec.get("cast"))

    def extract_value(self, item: dict[str, Any], extract_spec: dict[str, Any]) -> Any:
        kind = extract_spec.get("kind")
        if kind == "list_lookup":
            collection = self.get_path(item, extract_spec.get("path"), _MISSING)
            if collection is _MISSING or collection is None:
                return None
            if not isinstance(collection, list):
                raise ResponseParseError(f"extract path `{extract_spec.get('path')}` is not a list")

            match_field = extract_spec.get("match_field", "key")
            match_value = extract_spec.get("match_value")
            value_field = extract_spec.get("value_field", "value")
            for candidate in collection:
                if not isinstance(candidate, dict):
                    continue
                if candidate.get(match_field) == match_value:
                    return candidate.get(value_field)
            return None

        raise ResponseParseError(f"unsupported extract kind: {kind}")

    def build_bbox(self, item: dict[str, Any]) -> list[float]:
        bbox_rule = self.rules["bbox"]
        kind = bbox_rule["kind"]
        required = bool(bbox_rule.get("required", False))

        if kind == "xywh_to_xyxy":
            raw_bbox = self.get_path(item, bbox_rule["path"], _MISSING)
            if raw_bbox is _MISSING:
                if required:
                    raise ResponseParseError(f"missing bbox path `{bbox_rule['path']}`")
                raw_bbox = []
            if not isinstance(raw_bbox, list):
                raise ResponseParseError(f"bbox path `{bbox_rule['path']}` is not a list: {raw_bbox}")
            raw_bbox = list(raw_bbox)[:4]
            if required and len(raw_bbox) < 4:
                raise ResponseParseError(f"bbox path `{bbox_rule['path']}` must contain 4 values")
            while len(raw_bbox) < 4:
                raw_bbox.append(bbox_rule.get("default", 0))

            cast_name = bbox_rule.get("cast")
            x1, y1, w, h = [self.apply_cast(value, cast_name) for value in raw_bbox]
            if bbox_rule.get("center"):
                half_w = w / 2
                half_h = h / 2
                return [x1 - half_w, y1 - half_h, x1 + half_w, y1 + half_h]
            return [x1, y1, x1 + w, y1 + h]

        if kind == "xyxy_from_paths":
            values = []
            cast_name = bbox_rule.get("cast")
            default = bbox_rule.get("default", 0)
            for path in bbox_rule["paths"]:
                value = self.get_path(item, path, _MISSING)
                if value is _MISSING:
                    if required:
                        raise ResponseParseError(f"missing bbox path `{path}`")
                    value = default
                values.append(self.apply_cast(value, cast_name))
            return values

        if kind == "xywh_from_paths":
            values = []
            cast_name = bbox_rule.get("cast")
            default = bbox_rule.get("default", 0)
            for path in bbox_rule["paths"]:
                value = self.get_path(item, path, _MISSING)
                if value is _MISSING:
                    if required:
                        raise ResponseParseError(f"missing bbox path `{path}`")
                    value = default
                values.append(self.apply_cast(value, cast_name))
            x1, y1, w, h = values
            if bbox_rule.get("center"):
                half_w = w / 2
                half_h = h / 2
                return [x1 - half_w, y1 - half_h, x1 + half_w, y1 + half_h]
            return [x1, y1, x1 + w, y1 + h]

        if kind == "passthrough":
            value = self.get_path(item, bbox_rule["path"], _MISSING)
            if value is _MISSING or value is None:
                if required:
                    raise ResponseParseError(f"missing bbox path `{bbox_rule['path']}`")
                value = bbox_rule.get("default", [])
            if not isinstance(value, (list, tuple)):
                raise ResponseParseError(f"bbox path `{bbox_rule['path']}` is not a list: {value}")
            if required and len(value) < 4:
                raise ResponseParseError(f"bbox path `{bbox_rule['path']}` must contain at least 4 values")
            cast_name = bbox_rule.get("cast")
            values = [self.apply_cast(entry, cast_name) for entry in list(value)[:4]]
            while len(values) < 4:
                values.append(bbox_rule.get("default", 0))
            return values

        raise ValueError(f"unsupported bbox kind: {kind}")

    def get_extra_output_fields(self, item: dict[str, Any]) -> dict[str, Any]:
        extra_fields = {}
        for field_spec in self.rules.get("extra_fields", []):
            extra_fields[field_spec["name"]] = self.resolve_field(item, field_spec)
        extra_fields.update(self.get_hook_extra_fields(item))
        return extra_fields

    def get_hook_extra_fields(self, item: dict[str, Any]) -> dict[str, Any]:
        return {}

    @abstractmethod
    def build_output(self, item: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class DetectionMapper(RuleBasedResponseMapper):
    def build_detection(self, *, label: str | None, bbox: list[float], conf: float, **extra: Any) -> dict[str, Any]:
        detection = {
            "label": label,
            "bbox": bbox,
            "conf": conf,
        }
        detection.update(extra)
        return detection

    def build_output(self, item: dict[str, Any]) -> dict[str, Any]:
        label = self.resolve_field(item, self.rules["label"])
        conf = self.resolve_field(item, self.rules["conf"])
        bbox = self.build_bbox(item)
        extra_fields = self.get_extra_output_fields(item)
        return self.build_detection(label=label, bbox=bbox, conf=conf, **extra_fields)


class OCRMapper(RuleBasedResponseMapper):
    def build_ocr(self, *, bbox: list[float], text: str, **extra: Any) -> dict[str, Any]:
        result = {
            "bbox": bbox,
            "number": text,
        }
        result.update(extra)
        return result

    def build_output(self, item: dict[str, Any]) -> dict[str, Any]:
        text = self.resolve_field(item, self.rules["text"])
        bbox = self.build_bbox(item)
        extra_fields = self.get_extra_output_fields(item)
        return self.build_ocr(bbox=bbox, text=text, **extra_fields)


class CountMapper(ResponseMapper):
    def map(self, response_json: dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any] | None:
        return response_json


class ConfigurableDetectionMapper(DetectionMapper):
    def __init__(
        self,
        *,
        rules: dict[str, Any],
        names: list[str] | dict[str, str] | dict[int, str] | None = None,
    ):
        super().__init__(rules=rules)
        self.id_to_name, self.name_to_id = self._normalize_names(names)

    def build_output(self, item: dict[str, Any]) -> dict[str, Any]:
        label = None
        if "label" in self.rules:
            label = self.resolve_field(item, self.rules["label"])

        class_id = None
        if "class_id" in self.rules:
            class_id = self.resolve_field(item, self.rules["class_id"])

        if label is None and class_id is not None and self.id_to_name:
            label = self.id_to_name.get(int(class_id))

        if class_id is None and label is not None and self.name_to_id:
            class_id = self.name_to_id.get(str(label))

        if label is None and class_id is None:
            raise ResponseParseError("label and class_id are both missing after parsing")

        conf = self.resolve_field(item, self.rules["conf"])
        bbox = self.build_bbox(item)
        extra_fields = self.get_extra_output_fields(item)
        if class_id is not None:
            extra_fields["class_id"] = int(class_id)

        return self.build_detection(label=label, bbox=bbox, conf=conf, **extra_fields)

    def _normalize_names(
        self,
        names: list[str] | dict[str, str] | dict[int, str] | None,
    ) -> tuple[dict[int, str], dict[str, int]]:
        if names is None:
            return {}, {}

        if isinstance(names, list):
            id_to_name = {index: name for index, name in enumerate(names)}
            name_to_id = {name: index for index, name in enumerate(names)}
            return id_to_name, name_to_id

        id_to_name = {int(key): value for key, value in names.items()}
        name_to_id = {value: key for key, value in id_to_name.items()}
        return id_to_name, name_to_id


class ConfigurableOCRMapper(OCRMapper):
    def __init__(self, *, rules: dict[str, Any]):
        super().__init__(rules=rules)


class ConfigurableCountMapper(CountMapper):
    def __init__(self, *, rules: dict[str, Any]):
        self.rules = deepcopy(rules)


def parse_response_with_json_format(
    *,
    json_data: dict[str, Any],
    response_format: dict[str, Any],
) -> list[dict[str, Any]] | dict[str, Any] | None:
    try:
        rules = _normalize_response_rules(response_format)
        mapper = build_response_mapper_from_rules(rules)
        result = mapper.map(json_data)
        return result
    except Exception as exc:
        if isinstance(exc, ResponseParseError):
            raise
        raise ResponseParseError(f"parse failed: {exc}") from exc


def build_response_mapper_from_rules(rules: dict[str, Any]) -> ResponseMapper:
    normalized_rules = _normalize_response_rules(rules)
    output_type = normalized_rules.get("output_type", "detection")
    names = normalized_rules.get("names")

    if output_type == "detection":
        return ConfigurableDetectionMapper(rules=normalized_rules, names=names)
    if output_type == "ocr":
        return ConfigurableOCRMapper(rules=normalized_rules)
    if output_type == "count":
        return ConfigurableCountMapper(rules=normalized_rules)

    raise ResponseParseError(f"unsupported output_type: {output_type}")


def load_response_rules(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return deepcopy(source)

    rule_path = Path(source)
    with rule_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalize_response_rules(response_format: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response_format, dict):
        raise ResponseParseError("response_format must be a dict")

    if "rules" in response_format:
        rules = response_format["rules"]
        if not isinstance(rules, dict):
            raise ResponseParseError("response_format.rules must be a dict")
        return rules

    return response_format
