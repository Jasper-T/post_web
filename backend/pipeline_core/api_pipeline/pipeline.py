from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal

from .protocol import Protocol
from .request import RequestInput, normalize_input
from .storage.base import resolve_storage
from .transport import BaseTransport, RequestSpec, TransportKind, TransportResponse, create_transport


class ApiPipeline:
    """Transport-level API execution pipeline.

    Responsibilities:
    1. build request header/body from protocol/json template
    2. execute request through a transport implementation
    3. save raw response json when requested
    4. normalize transport exceptions
    """

    def __init__(
        self,
        url: str,
        protocol: Protocol,
        method: Literal["POST", "GET", "PUT", "PATCH", "DELETE"] = "POST",
        connect_timeout: float = 3,
        read_timeout: float = 30,
        storage: str | None = "json",
        storage_kwargs: dict | None = None,
        transport: TransportKind = "http",
        transport_impl: BaseTransport | None = None,
    ):
        self.url = url
        self.method = method.upper()
        self.protocol = protocol
        self.storage = resolve_storage(storage, storage_kwargs or {"save_dir": "./results"})
        self.timeout = (connect_timeout, read_timeout)
        self.transport_kind = transport
        self.transport = transport_impl or create_transport(transport, timeout=self.timeout)

    def _build_request(self, inputs: RequestInput) -> RequestSpec:
        request_spec = self.protocol.build_request(
            url=self.url,
            method=self.method,
            inputs=inputs,
        )
        if request_spec.timeout is None:
            request_spec.timeout = self.timeout
        return request_spec

    def _send_request(self, request_spec: RequestSpec) -> TransportResponse:
        start_time = time.time()
        response = self.transport.send(request_spec)
        cost = time.time() - start_time
        print(f"request success, cost: {round(cost, 3)}s")
        return response

    def _handle_request_error(self, error: Exception) -> None:
        normalized = self.transport.normalize_error(error)
        print(str(normalized))
        raise normalized

    def run_json(
        self,
        inputs: RequestInput | dict | str | Path,
        *,
        save: bool = False,
        save_name: str = "request",
        **kwargs,
    ) -> dict[str, Any]:
        req_input = normalize_input(inputs, **kwargs)

        try:
            request_spec = self._build_request(req_input)
            response = self._send_request(request_spec)
            response_json = response.json()

            if save and self.storage:
                self.storage.save(save_name=save_name, data=response_json)

            return response_json
        except Exception as error:
            self._handle_request_error(error)

    def run_data(
        self,
        inputs: RequestInput | dict | str | Path,
        **kwargs,
    ) -> Any:
        response_json = self.run_json(inputs, **kwargs)
        if not isinstance(response_json, dict):
            return None
        return response_json.get("data")

    def run_response(
        self,
        inputs: RequestInput | dict | str | Path,
        **kwargs,
    ) -> TransportResponse:
        req_input = normalize_input(inputs, **kwargs)

        try:
            request_spec = self._build_request(req_input)
            return self._send_request(request_spec)
        except Exception as error:
            self._handle_request_error(error)

    def run_raw(
        self,
        headers: dict | None = None,
        body: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        return self.run_json(
            RequestInput(headers=headers, body=body),
            **kwargs,
        )
