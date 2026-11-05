"""
Every HTTP request measured and traced: its duration by method, route
template and status class (Prometheus), and a server span that continues
the caller's trace when it sent a `traceparent`. The trace's id joins the
log context, so the request's log lines name it. Requests other than
probes and scrapes also count for the API availability SLI, and as slow
(LOG-04) when their answer started 2 s or more after they came in: a
stream (live events, an export) is as slow as its first byte, never as
long as it stays open. A route that waits for the language model or a
large upload by design is never slow here: the model's time has its own
service level (answer latency).
"""

import re
import time

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.contracts.service_metrics import ServiceMetricsContract
from app.gateways.failure_signals import FailureSignals
from app.gateways.http.middleware.request_deadline_middleware import (
    LONG_DEADLINE_PATTERNS,
)
from app.gateways.metrics.api_availability_tally import ApiAvailabilityTally
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
UNTRACED_PATHS: frozenset[str] = frozenset(
    {"/healthz", "/healthz/pipeline", "/readyz", "/metrics"}
)
SERVER_ERROR: int = 500
# Routes whose answer waits for the model or a large upload: the long
# deadline's routes (assembling an assistant, the test chat, autotests,
# imports, suggestions, attachments) and the public demo chat.
MODEL_BOUND_PATTERNS: tuple[re.Pattern[str], ...] = (
    *LONG_DEADLINE_PATTERNS,
    re.compile(r"^/v1/public-demos/[^/]+/messages$"),
)


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
        api_availability: ApiAvailabilityTally | None = None,
        failure_signals: FailureSignals | None = None,
    ) -> None:
        self._app: ASGIApp = app
        self._metrics: ServiceMetricsContract = metrics
        self._tracer: SpanTracer = tracer
        self._api_availability: ApiAvailabilityTally | None = api_availability
        self._failure_signals: FailureSignals | None = failure_signals

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        method: str = str(scope["method"])
        started: float = time.perf_counter()
        status: list[int] = [SERVER_ERROR]
        answer_started: list[float] = []

        async def send_with_status(message: Message) -> None:
            if message["type"] == "http.response.start":
                status[0] = int(message["status"])
                answer_started.append(time.perf_counter())
            await send(message)

        is_probe: bool = scope["path"] in UNTRACED_PATHS
        try:
            if is_probe:
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
            elapsed: float = max(0.0, time.perf_counter() - started)
            if self._api_availability is not None and not is_probe:
                self._api_availability.count(status[0])
            if self._failure_signals is not None and not (
                is_probe or waits_for_model(str(scope["path"]))
            ):
                waited: float = (
                    max(0.0, answer_started[0] - started) if answer_started else elapsed
                )
                self._failure_signals.count_if_slow(waited)
            self._metrics.observe_http_request(
                HttpRequestObservation(
                    method=MetricsLabel(method),
                    route=route_template(scope),
                    status_code=HttpStatusCode(status[0]),
                    duration=ObservedSeconds(elapsed),
                )
            )


def waits_for_model(path: str) -> bool:
    """Whether the route's answer waits for the model or a large upload."""

    return any(pattern.match(path) for pattern in MODEL_BOUND_PATTERNS)


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
