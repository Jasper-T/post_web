from __future__ import annotations

from copy import deepcopy
import re
import time
from typing import Any

from backend.pipeline_core.api_pipeline.request import RequestInput

from .base import BaseImageProtocol
PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")


class JsonTemplateProtocol(BaseImageProtocol):
    """Protocol built from imported header/body JSON templates."""

    PLACEHOLDER_CONTEXT = {
        "timestamp": "unix_timestamp",
        "image_b64": "image_base64",
        "image_width": "image_width",
        "image_height": "image_height",
        "image_url": "image_url",
    }

    def __init__(
        self,
        *,
        display_name: str,
        header_template: dict[str, Any] | None,
        body_template: dict[str, Any] | None,
        post_config: dict[str, Any] | None = None,
    ):
        super().__init__(headers={})
        self.display_name = display_name
        self.header_template = header_template or {}
        self.body_template = body_template or {}
        self.post_config = post_config or {}

    def build_header(self, inputs: RequestInput | None = None) -> dict[str, Any]:
        context = self._build_context(inputs, include_image=False)
        header = self._render_header_template(deepcopy(self.header_template), context)
        if not isinstance(header, dict):
            raise TypeError("rendered header template must be a dict")

        if inputs is not None and inputs.headers:
            header = self._deep_merge(header, inputs.headers)

        return header

    def build_body(self, inputs: RequestInput) -> dict[str, Any]:
        body = deepcopy(self.body_template)
        if not isinstance(body, dict):
            raise TypeError("body template must be a dict")

        context = self._build_context(
            inputs,
            include_image=self._post_config_requires_image(),
        )
        self._apply_post_config_overrides(body, context)

        if inputs.body:
            body = self._deep_merge(body, inputs.body)

        return body

    def _post_config_requires_image(self) -> bool:
        placeholder_paths = self.post_config.get("placeholderPaths") or {}
        if not isinstance(placeholder_paths, dict):
            return False
        image_keys = {"image_b64", "image_width", "image_height"}
        return any(placeholder_paths.get(key) for key in image_keys)

    def _build_context(self, inputs: RequestInput | None, *, include_image: bool) -> dict[str, Any]:
        context = {
            "display_name": self.display_name,
            "unix_timestamp": int(time.time()),
            "unix_timestamp_ms": int(time.time() * 1000),
        }

        if inputs is None:
            return context

        context.update(
            {
                "image_path": str(inputs.image_path) if inputs.image_path is not None else None,
                "image_url": inputs.image_url,
                "prompt": inputs.prompt,
                "text": inputs.text,
                "extra": deepcopy(inputs.extra),
                "headers": deepcopy(inputs.headers) if inputs.headers else {},
                "body": deepcopy(inputs.body) if inputs.body else {},
            }
        )

        if include_image and inputs.image_path is not None:
            image_base64, width, height = self.read_image_payload(inputs.image_path)
            context.update(
                {
                    "image_base64": image_base64,
                    "image_width": width,
                    "image_height": height,
                }
            )
        elif include_image and inputs.image_base64 is not None:
            context["image_base64"] = inputs.image_base64

        return context

    def _render_header_template(self, value: Any, context: dict[str, Any]) -> Any:
        if isinstance(value, dict):
            return {
                key: self._render_header_template(child, context)
                for key, child in value.items()
            }

        if isinstance(value, list):
            return [self._render_header_template(child, context) for child in value]

        if not isinstance(value, str):
            return value

        match = PLACEHOLDER_RE.fullmatch(value)
        if match:
            return self._resolve_context(context, match.group(1))

        def _replace(match_obj: re.Match[str]) -> str:
            resolved = self._resolve_context(context, match_obj.group(1))
            return "" if resolved is None else str(resolved)

        return PLACEHOLDER_RE.sub(_replace, value)

    def _resolve_context(self, context: dict[str, Any], path: str) -> Any:
        current: Any = context
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            if part not in current:
                return None
            current = current[part]
        return current

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(base)
        for key, value in override.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged

    def _apply_post_config_overrides(self, body: dict[str, Any], context: dict[str, Any]) -> None:
        placeholder_paths = self.post_config.get("placeholderPaths") or {}
        placeholder_types = self.post_config.get("placeholderTypes") or {}
        if not isinstance(placeholder_paths, dict):
            return

        for placeholder_key, target_path in placeholder_paths.items():
            if not target_path:
                continue
            context_path = self.PLACEHOLDER_CONTEXT.get(placeholder_key)
            if context_path is None:
                continue
            value = self._resolve_context(context, context_path)
            if value is None:
                continue
            value_type = placeholder_types.get(placeholder_key) if isinstance(placeholder_types, dict) else None
            self._set_path(body, str(target_path), self._coerce_post_config_value(value, value_type))

    def _coerce_post_config_value(self, value: Any, value_type: Any) -> Any:
        if value_type == "string":
            return str(value)
        if value_type == "int":
            return int(value)
        if value_type == "float":
            return float(value)
        if value_type == "bool":
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "on"}
            return bool(value)
        if value_type == "array":
            return value if isinstance(value, list) else [value]
        if value_type == "object":
            return value if isinstance(value, dict) else {"value": value}
        return value

    def _set_path(self, data: dict[str, Any], path: str, value: Any) -> None:
        parts = [part for part in path.split(".") if part != ""]
        if not parts:
            return

        current: Any = data
        for index, part in enumerate(parts[:-1]):
            next_part = parts[index + 1]
            if isinstance(current, list):
                item_index = int(part)
                while len(current) <= item_index:
                    current.append([] if next_part.isdigit() else {})
                if current[item_index] is None:
                    current[item_index] = [] if next_part.isdigit() else {}
                current = current[item_index]
                continue

            if part not in current or not isinstance(current[part], (dict, list)):
                current[part] = [] if next_part.isdigit() else {}
            current = current[part]

        last_part = parts[-1]
        if isinstance(current, list):
            item_index = int(last_part)
            while len(current) <= item_index:
                current.append(None)
            current[item_index] = value
        else:
            current[last_part] = value
