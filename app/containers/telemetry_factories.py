"""Factories of the process's metrics and tracing objects (for the containers)."""

from app.clients.postgres.pool_instruments import PoolInstruments
from app.clients.postgres.traced_cursor import traced_cursor_class
from app.contracts.service_metrics import ServiceMetricsContract
from app.schemas.configurations.app_settings import AppSettings
from app.utilities.observability.tracing.span_tracer import NullSpanTracer, SpanTracer


def is_sentry_tracing_enabled(settings: AppSettings) -> bool:
    """Sentry records performance traces (SENTRY_DSN and a rate above 0)."""

    return (
        settings.sentry_dsn is not None
        and float(settings.sentry_traces_sample_rate) > 0.0
    )


def build_pool_instruments(
    metrics: ServiceMetricsContract,
    span_tracer: SpanTracer,
) -> PoolInstruments:
    """The pool reports to the metrics; its statements are spans when tracing."""

    return PoolInstruments(
        metrics=metrics,
        cursor_class=(
            None
            if isinstance(span_tracer, NullSpanTracer)
            else traced_cursor_class(span_tracer)
        ),
    )
