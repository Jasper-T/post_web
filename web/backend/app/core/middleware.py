from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        started_at = perf_counter()
        client_host = request.client.host if request.client else "-"
        request_logger = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=client_host,
        )

        request_logger.info(
            "Request started request_id={} method={} path={} client={}",
            request_id,
            request.method,
            request.url.path,
            client_host,
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000
            request_logger.exception(
                "Request failed request_id={} method={} path={} duration_ms={:.2f}",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = (perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id
        level = "ERROR" if response.status_code >= 500 else "WARNING" if response.status_code >= 400 else "INFO"
        request_logger.log(
            level,
            "Request completed request_id={} method={} path={} status={} duration_ms={:.2f}",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
