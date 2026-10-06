"""
The start and the end of a process's telemetry: the service name its spans
carry (the API's or a worker's, unless OTEL_SERVICE_NAME names one), the
spans of its calls to providers (httpx, with OpenTelemetry on; Sentry's
HttpxIntegration makes its own) and, on the way out, the spans still
waiting in the batch, sent.
"""

import logging
import os

from opentelemetry.sdk.trace import TracerProvider

from app.containers.app import AppContainer
from app.utilities.observability.tracing.http_client_spans import (
    install_http_client_spans,
)
from app.utilities.observability.tracing.open_telemetry_setup import (
    INSTRUMENTATION_NAME,
)
from app.utilities.observability.tracing.open_telemetry_span_tracer import (
    OpenTelemetrySpanTracer,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
SERVICE_NAME_VARIABLE: str = "OTEL_SERVICE_NAME"
API_SERVICE_NAME: str = "workshop-api"
WORKER_SERVICE_NAME: str = "workshop-worker"


def name_service(service_name: str) -> None:
    """
    The entry point's default service name, before its container reads the
    settings; an OTEL_SERVICE_NAME of the environment wins.
    """

    os.environ.setdefault(SERVICE_NAME_VARIABLE, service_name)


def start_telemetry(app_container: AppContainer) -> None:
    """Spans for the process's provider calls when OpenTelemetry is on."""

    provider: TracerProvider | None = app_container.utilities.tracer_provider()
    if provider is not None:
        install_http_client_spans(
            OpenTelemetrySpanTracer(provider.get_tracer(INSTRUMENTATION_NAME))
        )


def finish_telemetry(app_container: AppContainer) -> None:
    """Send the spans still batched and stop the exporter (no-op without one)."""

    provider: TracerProvider | None = app_container.utilities.tracer_provider()
    if provider is None:
        return

    try:
        provider.shutdown()
    except Exception as error:  # noqa: BLE001 - shutting down must go on
        LOGGER.warning("Spans could not be sent on shutdown: %s", error)
