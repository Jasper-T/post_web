from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from backend.pipeline_core.protocols.mappers import (
    ResponseMapper,
    ResponseParseError,
    build_response_mapper_from_rules,
    load_response_rules,
    parse_response_with_json_format,
)
from .protocol import Protocol
from .request import RequestInput, normalize_input
from .transport import TransportKind

if TYPE_CHECKING:
    from .pipeline import ApiPipeline
    from backend.pipeline_core.protocols.template_protocol import JsonTemplateProtocol

@dataclass(slots=True)
class ResponseParserConfig:
    rules: dict[str, Any] | None = None
    rule_json: str | Path | None = None
    template_input: dict[str, Any] | None = None


@dataclass(slots=True)
class RequestPipelineBundle:
    display_name: str
    url: str
    transport: TransportKind
    protocol: Protocol
    pipeline: "ApiPipeline"
    response_mapper: ResponseMapper
    default_inputs: dict[str, Any] | None = None

    def run(
        self,
        inputs,
        *,
        save: bool = False,
        save_name: str = "request",
        **kwargs,
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        inputs = self._merge_inputs(inputs)
        response_json = self.pipeline.run_json(
            inputs,
            save=save,
            save_name=save_name,
            **kwargs,
        )
        result = self.response_mapper.map(response_json)

        if result is None:
            print("parse response failed")
            return None
        if isinstance(result, list) and not result:
            print("no detection")
            return []
        return result

    def run_json(self, inputs, **kwargs) -> dict[str, Any]:
        inputs = self._merge_inputs(inputs)
        return self.pipeline.run_json(inputs, **kwargs)

    def run_data(self, inputs, **kwargs) -> Any:
        inputs = self._merge_inputs(inputs)
        return self.pipeline.run_data(inputs, **kwargs)

    def run_response(self, inputs, **kwargs):
        inputs = self._merge_inputs(inputs)
        return self.pipeline.run_response(inputs, **kwargs)

    def parse_response(
        self,
        *,
        json_data: dict[str, Any],
        response_format: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        if response_format is None:
            try:
                return self.response_mapper.map(json_data)
            except Exception as exc:
                raise ResponseParseError(f"parse failed: {exc}") from exc
        return parse_response_with_json_format(
            json_data=json_data,
            response_format=response_format,
        )

    def _merge_inputs(self, inputs) -> RequestInput:
        request_input = normalize_input(inputs)
        if not self.default_inputs:
            return request_input

        merged_headers = _deep_merge_dicts(self.default_inputs.get("headers"), request_input.headers)
        merged_body = _deep_merge_dicts(self.default_inputs.get("body"), request_input.body)
        merged_extra = _deep_merge_dicts(self.default_inputs.get("extra"), request_input.extra)

        request_input.headers = merged_headers
        request_input.body = merged_body
        request_input.extra = merged_extra
        return request_input


def load_json_file(path: str | Path) -> dict[str, Any]:
    json_path = Path(path)
    with json_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def create_json_template_protocol(
    *,
    display_name: str,
    header_json: str | Path | dict[str, Any] | None,
    body_json: str | Path | dict[str, Any] | None,
    post_config: dict[str, Any] | None = None,
) -> "JsonTemplateProtocol":
    from backend.pipeline_core.protocols.template_protocol import JsonTemplateProtocol

    header_template = _ensure_json_mapping(header_json)
    body_template = _ensure_json_mapping(body_json)

    return JsonTemplateProtocol(
        display_name=display_name,
        header_template=header_template,
        body_template=body_template,
        post_config=post_config,
    )


def create_protocol_application(
    *,
    display_name: str,
    url: str,
    protocol: Protocol,
    response_mapper: ResponseMapper,
    method: Literal["POST", "GET", "PUT", "PATCH", "DELETE"] = "POST",
    transport: TransportKind = "http",
    connect_timeout: float = 3,
    read_timeout: float = 30,
    storage: str | None = "json",
    storage_kwargs: dict[str, Any] | None = None,
    default_inputs: dict[str, Any] | None = None,
):
    from .pipeline import ApiPipeline

    pipeline = ApiPipeline(
        url=url,
        protocol=protocol,
        method=method,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        storage=storage,
        storage_kwargs=storage_kwargs,
        transport=transport,
    )

    return RequestPipelineBundle(
        display_name=display_name,
        url=url,
        transport=transport,
        protocol=protocol,
        pipeline=pipeline,
        response_mapper=response_mapper,
        default_inputs=default_inputs,
    )


def create_request_pipeline(
    *,
    display_name: str,
    url: str,
    header_json: str | Path | dict[str, Any] | None,
    body_json: str | Path | dict[str, Any] | None,
    response_config: ResponseParserConfig,
    method: Literal["POST", "GET", "PUT", "PATCH", "DELETE"] = "POST",
    transport: TransportKind = "http",
    connect_timeout: float = 3,
    read_timeout: float = 30,
    storage: str | None = "json",
    storage_kwargs: dict[str, Any] | None = None,
    default_inputs: dict[str, Any] | None = None,
    post_config: dict[str, Any] | None = None,
) -> RequestPipelineBundle:
    from .pipeline import ApiPipeline

    response_rules = _load_response_rules_config(response_config)
    response_mapper = build_response_mapper_from_rules(response_rules)

    if response_config.template_input is not None:
        response_mapper.map(response_config.template_input)

    protocol = create_json_template_protocol(
        display_name=display_name,
        header_json=header_json,
        body_json=body_json,
        post_config=post_config,
    )

    pipeline = ApiPipeline(
        url=url,
        protocol=protocol,
        method=method,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        storage=storage,
        storage_kwargs=storage_kwargs,
        transport=transport,
    )

    return RequestPipelineBundle(
        display_name=display_name,
        url=url,
        transport=transport,
        protocol=protocol,
        pipeline=pipeline,
        response_mapper=response_mapper,
        default_inputs=default_inputs,
    )


def _ensure_json_mapping(source: str | Path | dict[str, Any] | None) -> dict[str, Any]:
    if source is None:
        return {}
    if isinstance(source, dict):
        return source
    return load_json_file(source)


def _load_response_rules_config(response_config: ResponseParserConfig) -> dict[str, Any]:
    if response_config.rules is not None:
        return load_response_rules(response_config.rules)
    if response_config.rule_json is not None:
        return load_response_rules(response_config.rule_json)
    raise ValueError("response parser rules or rule_json is required")


def _deep_merge_dicts(
    base: dict[str, Any] | None,
    override: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if base is None and override is None:
        return None
    if base is None:
        return deepcopy(override)
    if override is None:
        return deepcopy(base)

    merged = deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged
