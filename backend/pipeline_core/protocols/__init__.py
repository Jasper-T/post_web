from __future__ import annotations

from importlib import import_module


__all__ = [
    "BaseImageProtocol",
    "ResponseMapper",
    "ResponseParseError",
    "DetectionMapper",
    "OCRMapper",
    "CountMapper",
    "ConfigurableDetectionMapper",
    "parse_response_with_json_format",
    "build_response_mapper_from_rules",
    "load_response_rules",
    "JsonTemplateProtocol",
]


_EXPORTS = {
    "BaseImageProtocol": ("backend.pipeline_core.protocols.base", "BaseImageProtocol"),
    "ResponseMapper": ("backend.pipeline_core.protocols.mappers", "ResponseMapper"),
    "ResponseParseError": ("backend.pipeline_core.protocols.mappers", "ResponseParseError"),
    "DetectionMapper": ("backend.pipeline_core.protocols.mappers", "DetectionMapper"),
    "OCRMapper": ("backend.pipeline_core.protocols.mappers", "OCRMapper"),
    "CountMapper": ("backend.pipeline_core.protocols.mappers", "CountMapper"),
    "ConfigurableDetectionMapper": ("backend.pipeline_core.protocols.mappers", "ConfigurableDetectionMapper"),
    "parse_response_with_json_format": ("backend.pipeline_core.protocols.mappers", "parse_response_with_json_format"),
    "build_response_mapper_from_rules": ("backend.pipeline_core.protocols.mappers", "build_response_mapper_from_rules"),
    "load_response_rules": ("backend.pipeline_core.protocols.mappers", "load_response_rules"),
    "JsonTemplateProtocol": ("backend.pipeline_core.protocols.template_protocol", "JsonTemplateProtocol"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
