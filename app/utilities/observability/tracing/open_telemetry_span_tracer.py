"""Spans to OpenTelemetry (exported over OTLP by the process's provider)."""

from collections.abc import Generator, Mapping
from contextlib import contextmanager

from opentelemetry import trace

from app.schemas.constants.telemetry import SpanKind
from app.schemas.typings.observability.constrained_strings import TraceParent
from app.utilities.observability.tracing.span_tracer import (
    SpanAttribute,
    SpanHandle,
    SpanTracer,
)
from app.utilities.observability.tracing.trace_context import parent_context

OTEL_SPAN_KINDS: dict[SpanKind, trace.SpanKind] = {
    SpanKind.SERVER: trace.SpanKind.SERVER,
    SpanKind.CLIENT: trace.SpanKind.CLIENT,
    SpanKind.CONSUMER: trace.SpanKind.CONSUMER,
    SpanKind.INTERNAL: trace.SpanKind.INTERNAL,
}


class OpenTelemetrySpanHandle(SpanHandle):
    def __init__(self, span: trace.Span) -> None:
        self._span: trace.Span = span

    def set_attribute(self, key: str, value: SpanAttribute) -> None:
        self._span.set_attribute(key, value)

    def rename(self, name: str) -> None:
        self._span.update_name(name)

    def mark_failed(self, error_type: str) -> None:
        self._span.set_attribute("error.type", error_type)
        self._span.set_status(trace.Status(trace.StatusCode.ERROR))


class OpenTelemetrySpanTracer(SpanTracer):
    """
    Spans of one tracer (of the process's TracerProvider). A span nests in
    the current one of this thread or task; `parent` starts it in another
    trace (a queued job continuing the request that queued it, a request
    whose caller sent its `traceparent`).
    """

    def __init__(self, tracer: trace.Tracer) -> None:
        self._tracer: trace.Tracer = tracer

    @property
    def is_recording(self) -> bool:
        return True

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind,
        attributes: Mapping[str, SpanAttribute],
        parent: TraceParent | None = None,
    ) -> Generator[SpanHandle]:
        with self._tracer.start_as_current_span(
            name,
            context=parent_context(parent),
            kind=OTEL_SPAN_KINDS[kind],
            attributes=dict(attributes),
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            handle = OpenTelemetrySpanHandle(span)
            try:
                yield handle
            except BaseException as error:
                handle.mark_failed(type(error).__name__)
                raise
