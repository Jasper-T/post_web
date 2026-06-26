from __future__ import annotations

from abc import abstractmethod
import json
import os
from pathlib import Path
from typing import Any

from backend.pipeline_core.api_pipeline.protocol import Protocol
from backend.pipeline_core.api_pipeline.request import RequestInput
from backend.pipeline_core.api_pipeline.helpers import encode_image_from_path, read_image_size


DATA_ROOT = Path(os.getenv("FUXING_DATA_ROOT", Path(__file__).resolve().parents[3] / "data")).resolve()
PIPELINE_TEMPLATE_DIR = DATA_ROOT / "templates"


class BaseImageProtocol(Protocol):
    """Shared image helpers for protocol adapters."""

    DEFAULT_HEADERS = {
        "Content-type": "application/json",
        "x-resource-service": "video-algo-process",
    }

    def __init__(self, headers: dict[str, Any] | None = None):
        self.headers = headers or {}

    def build_header(self, inputs: RequestInput | None = None) -> dict[str, Any]:
        headers = dict(self.DEFAULT_HEADERS)
        headers.update(self.headers)

        if inputs is not None and inputs.headers:
            headers.update(inputs.headers)

        return headers

    def validate_required_fields(self, inputs: RequestInput, *field_names: str) -> None:
        for field_name in field_names:
            if getattr(inputs, field_name) is None:
                raise ValueError(f"{field_name} is required")

    def require_image_path(self, inputs: RequestInput) -> Path:
        self.validate_required_fields(inputs, "image_path")
        return Path(inputs.image_path)

    def read_image_payload(self, image_path: str | Path) -> tuple[str, int, int]:
        image_path = Path(image_path)
        image_base64 = encode_image_from_path(str(image_path))
        width, height = read_image_size(str(image_path))
        return image_base64, width, height

    def load_template(self, template_name: str) -> dict[str, Any]:
        candidate_path = Path(template_name)
        if candidate_path.is_absolute():
            template_path = candidate_path
        else:
            direct_path = PIPELINE_TEMPLATE_DIR / candidate_path
            request_path = PIPELINE_TEMPLATE_DIR / "requests" / candidate_path
            response_path = PIPELINE_TEMPLATE_DIR / "responses" / candidate_path
            if direct_path.exists():
                template_path = direct_path
            elif request_path.exists():
                template_path = request_path
            else:
                template_path = response_path
        with template_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @abstractmethod
    def build_body(self, inputs: RequestInput) -> dict[str, Any]:
        raise NotImplementedError
