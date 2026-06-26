from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Mapping


@dataclass
class RequestInput:
    image_path: str | Path | None = None
    image_base64: str | None = None
    image_url: str | None = None
    prompt: str | None = None
    text: str | None = None
    headers: dict[str, Any] | None = None
    body: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def _build(cls, **kwargs) -> "RequestInput":
        field_names = {f.name for f in fields(cls)}

        known = {}
        raw_extra = {}

        for k, v in kwargs.items():
            if k in field_names and k != "extra":
                known[k] = v
            elif k == "extra":
                if v is None:
                    continue
                if not isinstance(v, dict):
                    raise TypeError("extra must be a dict")
                raw_extra.update(v)
            else:
                raw_extra[k] = v

        return cls(**known, extra=raw_extra)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RequestInput":
        return cls._build(**data)

    @classmethod
    def from_image(cls, image_path, **kwargs):
        return cls._build(image_path=image_path, **kwargs)

    @classmethod
    def from_url(cls, image_url, **kwargs):
        return cls._build(image_url=image_url, **kwargs)


def normalize_input(
    inputs: RequestInput | Mapping[str, Any] | str | Path,
    **kwargs,
) -> RequestInput:
    if isinstance(inputs, RequestInput):
        # 合并原有 extra 和新的 kwargs
        merged_extra = {**inputs.extra, **kwargs}
        # 返回新的 RequestInput，保持原对象不变
        return replace(inputs, extra=merged_extra)

    elif isinstance(inputs, (str, Path)):
        return RequestInput.from_image(inputs, **kwargs)

    elif isinstance(inputs, Mapping):
        # from_mapping 会把未识别字段放到 extra
        req_input = RequestInput.from_mapping(inputs)
        # 再合并 kwargs
        req_input.extra = {**req_input.extra, **kwargs}
        return req_input

    else:
        raise TypeError(
            f"unsupported input type: {type(inputs).__name__}, "
            "expected RequestInput, dict, str or Path"
        )