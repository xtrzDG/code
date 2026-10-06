"""
Every HTTP request measured and traced: its duration by method, route
template and status class (Prometheus), and a server span that continues
the caller's trace when it sent a `traceparent`. The trace's id joins the
log context, so the request's log lines name it.
"""

import time

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.contracts.service_metrics import ServiceMetricsContract
from app.schemas.constants.telemetry import SpanKind
from app.schemas.dto.telemetry import HttpRequestObservation
from app.schemas.typings.observability.constrained_floats import ObservedSeconds
from app.schemas.typings.observability.constrained_integers import HttpStatusCode
from app.schemas.typings.observability.constrained_strings import (
    MetricsLabel,
    TraceParent,
)
from app.utilities.observability.log_context import bound_log_context
from app.utilities.observability.tracing.span_tracer import SpanHandle, SpanTracer
from app.utilities.observability.tracing.trace_context import (
    TRACEPARENT_HEADER,
    current_trace_id,
)

# Requests no route answered: one label, whatever their paths.
UNMATCHED_ROUTE: MetricsLabel = MetricsLabel("unmatched")
# Probes and scrapes are measured, never traced (they would fill traces).
UNTRACED_PATHS: frozenset[str] = frozenset({"/healthz", "/readyz", "/metrics"})
SERVER_ERROR: int = 500


class RequestTelemetryMiddleware:
    """
    Pure ASGI middleware inside the request-id layer: the request id is
    bound before it runs, so the span, the metrics and the trace id belong
    to the same request.
    """

    def __init__(
        self,
        app: ASGIApp,
        metrics: ServiceMetricsContract,
        tracer: SpanTracer,
    ) -> None:
        self._app: ASGIApp = app
        self._metrics: ServiceMetricsContract = metrics
        self._tracer: SpanTracer = tracer

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        method: str = str(scope["method"])
        started: float = time.perf_counter()
        status: list[int] = [SERVER_ERROR]

        async def send_with_status(message: Message) -> None:
            if message["type"] == "http.response.start":
                status[0] = int(message["status"])
            await send(message)

        try:
            if scope["path"] in UNTRACED_PATHS:
                await self._app(scope, receive, send_with_status)
                return

            with (
                self._tracer.span(
                    method,
                    SpanKind.SERVER,
                    {"http.request.method": method},
                    parent=caller_trace_parent(scope),
                ) as span,
                bound_log_context(trace_id=current_trace_id()),
            ):
                try:
                    await self._app(scope, receive, send_with_status)
                finally:
                    name_span(span, method, route_template(scope), status[0])
        finally:
            self._metrics.observe_http_request(
                HttpRequestObservation(
                    method=MetricsLabel(method),
                    route=route_template(scope),
                    status_code=HttpStatusCode(status[0]),
                    duration=ObservedSeconds(max(0.0, time.perf_counter() - started)),
                )
            )


def route_template(scope: Scope) -> MetricsLabel:
    """The template of the route that answered (`/v1/businesses/{business_id}`)."""

    path: object = getattr(scope.get("route"), "path", None)
    if not isinstance(path, str) or not path:
        return UNMATCHED_ROUTE

    return MetricsLabel(path)


def caller_trace_parent(scope: Scope) -> TraceParent | None:
    """The caller's `traceparent` when it sent a valid one."""

    raw: str | None = Headers(scope=scope).get(TRACEPARENT_HEADER)
    if raw is None:
        return None

    try:
        return TraceParent(raw.strip().lower())
    except ValueError:
        return None


def name_span(span: SpanHandle, method: str, route: MetricsLabel, status: int) -> None:
    span.rename(f"{method} {route}")
    span.set_attribute("http.route", str(route))
    span.set_attribute("http.response.status_code", status)
    if status >= SERVER_ERROR:
        span.mark_failed(str(status))
