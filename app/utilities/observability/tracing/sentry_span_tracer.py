"""Spans inside Sentry's sampled performance traces (SENTRY_TRACES_SAMPLE_RATE)."""

from collections.abc import Generator, Mapping
from contextlib import contextmanager

import sentry_sdk
from sentry_sdk.tracing import Span

from app.schemas.constants.telemetry import SpanKind
from app.schemas.typings.observability.constrained_strings import TraceParent
from app.utilities.observability.tracing.span_tracer import (
    NULL_SPAN_HANDLE,
    SpanAttribute,
    SpanHandle,
    SpanTracer,
)

# Sentry's span operations by kind; a database span names its own ("db").
SENTRY_OPERATIONS: dict[SpanKind, str] = {
    SpanKind.SERVER: "http.server",
    SpanKind.CLIENT: "http.client",
    SpanKind.CONSUMER: "queue.process",
    SpanKind.INTERNAL: "function",
}
OPERATION_ATTRIBUTE: str = "sentry.op"


class SentrySpanHandle(SpanHandle):
    def __init__(self, span: Span) -> None:
        self._span: Span = span

    def set_attribute(self, key: str, value: SpanAttribute) -> None:
        self._span.set_data(key, value)

    def rename(self, name: str) -> None:
        self._span.description = name

    def mark_failed(self, error_type: str) -> None:
        self._span.set_data("error.type", error_type)
        self._span.set_status("internal_error")


class SentrySpanTracer(SpanTracer):
    """
    A child span of the Sentry transaction this code runs in, only when one
    runs (a sampled request): outside one, nothing is recorded, and a
    request's own span is the transaction Sentry's integration makes. The
    operation comes from the `sentry.op` attribute, else from the kind.
    """

    def __init__(self, is_enabled: bool) -> None:
        self._is_enabled: bool = is_enabled

    @property
    def is_recording(self) -> bool:
        return self._is_enabled and sentry_sdk.get_current_span() is not None

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind,
        attributes: Mapping[str, SpanAttribute],
        parent: TraceParent | None = None,
    ) -> Generator[SpanHandle]:
        # Sentry's transactions carry their own trace; a parent is not used.
        # Its FastAPI integration makes the request's transaction itself.
        del parent
        if kind is SpanKind.SERVER or not self.is_recording:
            yield NULL_SPAN_HANDLE
            return

        operation: SpanAttribute = attributes.get(
            OPERATION_ATTRIBUTE, SENTRY_OPERATIONS[kind]
        )
        with sentry_sdk.start_span(op=str(operation), name=name) as span:
            for key, value in attributes.items():
                if key != OPERATION_ATTRIBUTE:
                    span.set_data(key, value)
            handle = SentrySpanHandle(span)
            try:
                yield handle
            except BaseException as error:
                handle.mark_failed(type(error).__name__)
                raise
