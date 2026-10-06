"""Prometheus metrics of this API process (or instance): GET /metrics."""

import hmac
from collections.abc import Callable

import anyio
import anyio.to_thread
from fastapi import APIRouter, Request, Response

from app.gateways.http.openapi_error_contract import standard_error_responses
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    NotFoundError,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.observability.metrics.metrics_exposition import MetricsPage

METRICS_PATH: str = "/metrics"
BEARER_PREFIX: str = "Bearer "
# A scrape reads the job queue's depth from the database: on threads of its
# own, never on the request threads.
METRICS_THREADS: int = 1

type MetricsRenderer = Callable[[], MetricsPage]


def build_metrics_router(
    metrics_token: PlatformSecret | None,
    render: MetricsRenderer,
) -> APIRouter:
    """
    Route (not in the API description):
        GET /metrics   the Prometheus text exposition: request durations by
                       route, webhooks, model calls, the connection pool,
                       circuit breakers, the job queue's depth and age
                       (docs/operations/observability.md). Only with
                       `Authorization: Bearer <METRICS_TOKEN>` (401
                       otherwise); 404 when METRICS_TOKEN is not set.
    """

    router = APIRouter(responses=standard_error_responses())
    limiters: list[anyio.CapacityLimiter] = []

    @router.get(METRICS_PATH, include_in_schema=False)
    async def read_metrics(request: Request) -> Response:
        if metrics_token is None:
            raise NotFoundError("Metrics are not enabled on this instance.")

        if not is_authorized(request.headers.get("authorization"), metrics_token):
            raise AuthenticationRequiredError("A valid metrics token is required.")

        if not limiters:
            limiters.append(anyio.CapacityLimiter(METRICS_THREADS))
        page: MetricsPage = await anyio.to_thread.run_sync(render, limiter=limiters[0])
        return Response(content=page.body, media_type=page.content_type)

    return router


def is_authorized(authorization: str | None, token: PlatformSecret) -> bool:
    """Whether the header carries the token (compared in constant time)."""

    if authorization is None or not authorization.startswith(BEARER_PREFIX):
        return False

    offered: str = authorization.removeprefix(BEARER_PREFIX).strip()
    return hmac.compare_digest(offered.encode(), str(token).encode())
