from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


TransportKind = Literal["http", "grpc", "websocket"]


@dataclass(slots=True)
class RequestSpec:
    transport: TransportKind = "http"
    method: str = "POST"
    url: str | None = None
    headers: dict[str, Any] = field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    body: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timeout: tuple[float, float] | None = None


@dataclass(slots=True)
class TransportResponse:
    status_code: int | None
    headers: dict[str, Any]
    body: Any
    raw_response: Any = None

    def json(self) -> dict[str, Any]:
        if isinstance(self.body, dict):
            return self.body
        raise TypeError("transport response body is not a json object")


class BaseTransport:
    def __init__(self, *, timeout: tuple[float, float] | None = None):
        self.timeout = timeout

    def send(self, request_spec: RequestSpec) -> TransportResponse:
        raise NotImplementedError

    def normalize_error(self, error: Exception) -> Exception:
        return error


class HttpTransport(BaseTransport):
    def __init__(self, *, timeout: tuple[float, float] | None = None):
        super().__init__(timeout=timeout)
        import requests

        self._requests = requests
        self._session = requests.Session()

    def send(self, request_spec: RequestSpec) -> TransportResponse:
        response = self._session.request(
            request_spec.method,
            request_spec.url,
            headers=request_spec.headers,
            json=request_spec.json_body,
            data=request_spec.body,
            timeout=request_spec.timeout or self.timeout,
        )
        response.raise_for_status()

        try:
            body = response.json()
        except ValueError as exc:
            raise ValueError(f"response is not valid json: {exc}") from exc

        return TransportResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=body,
            raw_response=response,
        )

    def normalize_error(self, error: Exception) -> Exception:
        requests = self._requests

        if isinstance(error, requests.exceptions.Timeout):
            return TimeoutError(f"request timeout: {error}")

        if isinstance(error, requests.exceptions.ConnectionError):
            return RuntimeError(f"connection error: {error}")

        if isinstance(error, requests.exceptions.HTTPError):
            return RuntimeError(f"http error: {error}")

        return error


class GrpcTransport(BaseTransport):
    def send(self, request_spec: RequestSpec) -> TransportResponse:
        raise NotImplementedError(
            "grpc transport is reserved but not implemented yet; "
            "provide channel/stub metadata and serializer before enabling it"
        )


class WebSocketTransport(BaseTransport):
    def send(self, request_spec: RequestSpec) -> TransportResponse:
        raise NotImplementedError(
            "websocket transport is reserved but not implemented yet; "
            "provide connection/session lifecycle and message codec before enabling it"
        )


def create_transport(
    transport: TransportKind,
    *,
    timeout: tuple[float, float] | None = None,
) -> BaseTransport:
    if transport == "http":
        return HttpTransport(timeout=timeout)
    if transport == "grpc":
        return GrpcTransport(timeout=timeout)
    if transport == "websocket":
        return WebSocketTransport(timeout=timeout)
    raise ValueError(f"unsupported transport: {transport}")
