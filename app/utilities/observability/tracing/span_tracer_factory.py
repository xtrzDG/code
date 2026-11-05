from opentelemetry.sdk.trace import TracerProvider

from app.utilities.observability.tracing.open_telemetry_setup import (
    INSTRUMENTATION_NAME,
)
from app.utilities.observability.tracing.open_telemetry_span_tracer import (
    OpenTelemetrySpanTracer,
)
from app.utilities.observability.tracing.sentry_span_tracer import SentrySpanTracer
from app.utilities.observability.tracing.span_tracer import (
    NO_SPAN_TRACER,
    CombinedSpanTracer,
    SpanTracer,
)


def build_span_tracer(
    tracer_provider: TracerProvider | None,
    is_sentry_tracing_enabled: bool,
) -> SpanTracer:
    """
    The process's span tracer: OpenTelemetry with a provider, Sentry when
    its performance traces are on (SENTRY_DSN and a sample rate above 0),
    both, or one that records nothing.
    """

    tracers: list[SpanTracer] = []
    if tracer_provider is not None:
        tracers.append(
            OpenTelemetrySpanTracer(tracer_provider.get_tracer(INSTRUMENTATION_NAME))
        )

    if is_sentry_tracing_enabled:
        tracers.append(SentrySpanTracer(is_enabled=True))

    if not tracers:
        return NO_SPAN_TRACER

    return tracers[0] if len(tracers) == 1 else CombinedSpanTracer(tracers)
