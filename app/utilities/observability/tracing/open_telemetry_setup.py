"""
The process's OpenTelemetry tracer provider: spans batched to the OTLP/HTTP
collector of OTEL_EXPORTER_OTLP_ENDPOINT, a share of OTEL_TRACES_SAMPLE_RATE
of the traces this process starts (a trace started elsewhere keeps its
caller's decision). Without an endpoint there is no provider at all.
"""

import urllib.parse

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.schemas.configurations.telemetry_settings import TelemetrySettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.typings.platform.constrained_strings import ReleaseVersion

DEFAULT_SERVICE_NAME: str = "workshop-backend"
TRACES_PATH: str = "/v1/traces"
INSTRUMENTATION_NAME: str = "assistant-workshop"


def parse_otlp_headers(raw_headers: str | None) -> dict[str, str]:
    """`key=value,key2=value2` (values URL-encoded), as the OTLP spec writes them."""

    headers: dict[str, str] = {}
    if raw_headers is None:
        return headers

    for pair in raw_headers.split(","):
        key, separator, value = pair.partition("=")
        if separator and key.strip():
            headers[key.strip()] = urllib.parse.unquote(value.strip())

    return headers


def build_tracer_provider(
    settings: TelemetrySettings,
    environment: DeploymentEnvironment,
    release: ReleaseVersion | None,
    exporter: SpanExporter | None = None,
) -> TracerProvider | None:
    """
    The provider when tracing is configured (or `exporter` is given, in
    tests), else None. Spans leave in batches from a background thread, so
    a slow collector never slows a request.
    """

    if exporter is None:
        if settings.otlp_endpoint is None:
            return None

        exporter = OTLPSpanExporter(
            endpoint=str(settings.otlp_endpoint).rstrip("/") + TRACES_PATH,
            headers=parse_otlp_headers(
                None if settings.otlp_headers is None else str(settings.otlp_headers)
            ),
        )

    attributes: dict[str, str] = {
        "service.name": (
            DEFAULT_SERVICE_NAME
            if settings.otel_service_name is None
            else str(settings.otel_service_name)
        ),
        "deployment.environment.name": environment.value,
    }
    if release is not None:
        attributes["service.version"] = str(release)

    provider = TracerProvider(
        resource=Resource.create(attributes),
        sampler=ParentBased(TraceIdRatioBased(float(settings.otel_traces_sample_rate))),
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider
