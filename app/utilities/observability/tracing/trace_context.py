"""
The trace the running code belongs to: its id for log lines and the
quality journal, and its W3C `traceparent` for a job queued now, so the
job's spans continue the same trace (webhook -> job -> model -> send).

OpenTelemetry's current span wins; without one, a sampled Sentry
transaction's trace is used; outside both there is no trace.
"""

import sentry_sdk
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)

from app.schemas.typings.observability.constrained_strings import (
    TraceId,
    TraceParent,
)

TRACEPARENT_HEADER: str = "traceparent"
TRACE_CONTEXT: TraceContextTextMapPropagator = TraceContextTextMapPropagator()


def current_trace_id() -> TraceId | None:
    """The id of the trace this code runs in, if any."""

    context: trace.SpanContext = trace.get_current_span().get_span_context()
    if context.is_valid:
        return TraceId(trace.format_trace_id(context.trace_id))

    sentry_span = sentry_sdk.get_current_span()
    if sentry_span is None:
        return None

    try:
        return TraceId(str(sentry_span.trace_id))
    except ValueError:
        return None


def current_trace_parent() -> TraceParent | None:
    """The `traceparent` a job queued now continues (None outside a trace)."""

    carrier: dict[str, str] = {}
    TRACE_CONTEXT.inject(carrier)
    raw: str | None = carrier.get(TRACEPARENT_HEADER)
    if raw is None:
        return sentry_trace_parent()

    try:
        return TraceParent(raw)
    except ValueError:
        return None


def sentry_trace_parent() -> TraceParent | None:
    """The W3C form of the running Sentry span, when one runs."""

    sentry_span = sentry_sdk.get_current_span()
    if sentry_span is None:
        return None

    flags: str = "01" if sentry_span.sampled else "00"
    try:
        return TraceParent(f"00-{sentry_span.trace_id}-{sentry_span.span_id}-{flags}")
    except ValueError:
        return None


def parent_context(trace_parent: TraceParent | None) -> Context | None:
    """The OpenTelemetry context a span continuing `trace_parent` starts in."""

    if trace_parent is None:
        return None

    return TRACE_CONTEXT.extract({TRACEPARENT_HEADER: str(trace_parent)})
