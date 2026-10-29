"""
Spans of distributed traces, behind one small interface: OpenTelemetry
when OTEL_EXPORTER_OTLP_ENDPOINT is set, Sentry's performance traces when
a sampled Sentry transaction is running, both, or neither (nothing is
recorded and nothing costs more than a call).

Attributes are technical: route templates, statement names, tables, hosts,
status codes, models. Never parameters, texts, URLs with queries, or ids
of people.
"""

from collections.abc import Generator, Mapping, Sequence
from contextlib import AbstractContextManager, ExitStack, contextmanager
from typing import Protocol

from app.schemas.constants.telemetry import SpanKind
from app.schemas.typings.observability.constrained_strings import TraceParent

type SpanAttribute = str | int | float | bool


class SpanHandle(Protocol):
    """The span of a block, to note what is known only at its end."""

    def set_attribute(self, key: str, value: SpanAttribute) -> None:
        raise NotImplementedError

    def rename(self, name: str) -> None:
        """A better name known only at the end (a request's route template)."""
        raise NotImplementedError

    def mark_failed(self, error_type: str) -> None:
        """The work of the span failed (the error's type, never its text)."""
        raise NotImplementedError


class SpanTracer(Protocol):
    @property
    def is_recording(self) -> bool:
        """Whether spans go anywhere (else callers may skip their labels)."""
        raise NotImplementedError

    def span(
        self,
        name: str,
        kind: SpanKind,
        attributes: Mapping[str, SpanAttribute],
        parent: TraceParent | None = None,
    ) -> AbstractContextManager[SpanHandle]:
        """
        A span around the block; an error leaving it marks it failed. With
        `parent` (a job's or a caller's `traceparent`) it continues that
        trace instead of the current one.
        """
        raise NotImplementedError


class NullSpanHandle(SpanHandle):
    def set_attribute(self, key: str, value: SpanAttribute) -> None:
        del key, value

    def rename(self, name: str) -> None:
        del name

    def mark_failed(self, error_type: str) -> None:
        del error_type


NULL_SPAN_HANDLE: SpanHandle = NullSpanHandle()


class NullSpanTracer(SpanTracer):
    """Records nothing (tracing is off)."""

    @property
    def is_recording(self) -> bool:
        return False

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind,
        attributes: Mapping[str, SpanAttribute],
        parent: TraceParent | None = None,
    ) -> Generator[SpanHandle]:
        del name, kind, attributes, parent
        yield NULL_SPAN_HANDLE


NO_SPAN_TRACER: SpanTracer = NullSpanTracer()


class _CombinedSpanHandle(SpanHandle):
    def __init__(self, handles: Sequence[SpanHandle]) -> None:
        self._handles: tuple[SpanHandle, ...] = tuple(handles)

    def set_attribute(self, key: str, value: SpanAttribute) -> None:
        for handle in self._handles:
            handle.set_attribute(key, value)

    def rename(self, name: str) -> None:
        for handle in self._handles:
            handle.rename(name)

    def mark_failed(self, error_type: str) -> None:
        for handle in self._handles:
            handle.mark_failed(error_type)


class CombinedSpanTracer(SpanTracer):
    """One span in every tracer that records (OpenTelemetry and Sentry)."""

    def __init__(self, tracers: Sequence[SpanTracer]) -> None:
        self._tracers: tuple[SpanTracer, ...] = tuple(tracers)

    @property
    def is_recording(self) -> bool:
        return any(tracer.is_recording for tracer in self._tracers)

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind,
        attributes: Mapping[str, SpanAttribute],
        parent: TraceParent | None = None,
    ) -> Generator[SpanHandle]:
        with ExitStack() as stack:
            handles: list[SpanHandle] = [
                stack.enter_context(tracer.span(name, kind, attributes, parent))
                for tracer in self._tracers
                if tracer.is_recording
            ]
            yield _CombinedSpanHandle(handles)
