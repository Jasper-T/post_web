from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .request import RequestInput
from .transport import RequestSpec


class Protocol(ABC):
    """Request builder interface for transport-agnostic API execution."""

    @abstractmethod
    def build_header(self, inputs: RequestInput | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_body(self, inputs: RequestInput) -> dict[str, Any]:
        raise NotImplementedError

    def build_request(
        self,
        *,
        url: str,
        method: str,
        inputs: RequestInput,
    ) -> RequestSpec:
        return RequestSpec(
            transport="http",
            method=method,
            url=url,
            headers=self.build_header(inputs),
            json_body=self.build_body(inputs),
        )
