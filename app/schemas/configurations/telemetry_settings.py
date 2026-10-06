from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.observability.constrained_integers import MetricsPort
from app.schemas.typings.observability.constrained_strings import OtelServiceName
from app.schemas.typings.platform.constrained_floats import TraceSampleRate
from app.schemas.typings.platform.strings import LocalDirectoryPath, PlatformSecret

DEFAULT_OTEL_TRACES_SAMPLE_RATE: float = 0.1


class TelemetrySettings(ImmutableDTO):
    """
    Metrics and distributed traces (docs/operations/observability.md).

    Metrics: the API serves Prometheus metrics at GET /metrics and a worker
    on WORKER_METRICS_PORT, both only to `Authorization: Bearer
    <METRICS_TOKEN>`; without a token neither is served. With
    PROMETHEUS_MULTIPROC_DIR (several uvicorn workers in one instance) the
    processes share their series through files there.

    Traces: with OTEL_EXPORTER_OTLP_ENDPOINT, spans of requests, jobs,
    database statements and outgoing HTTP calls go to that OTLP/HTTP
    collector (OTEL_EXPORTER_OTLP_HEADERS authenticates), a share of
    OTEL_TRACES_SAMPLE_RATE of the traces started here; off otherwise.
    """

    metrics_token: PlatformSecret | None = Field(default=None, repr=False)
    worker_metrics_port: MetricsPort | None = None
    prometheus_multiproc_directory: LocalDirectoryPath | None = None
    otlp_endpoint: PublicBaseUrl | None = None
    otlp_headers: PlatformSecret | None = Field(default=None, repr=False)
    otel_service_name: OtelServiceName | None = None
    otel_traces_sample_rate: TraceSampleRate = TraceSampleRate(
        DEFAULT_OTEL_TRACES_SAMPLE_RATE
    )
