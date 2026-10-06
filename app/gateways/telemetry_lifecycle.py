"""
The start and the end of a process's telemetry: the service name its spans
carry (the API's or a worker's, unless OTEL_SERVICE_NAME names one) and,
on the way out, the spans still waiting in the batch, sent.
"""

import logging
import os

from opentelemetry.sdk.trace import TracerProvider

from app.containers.app import AppContainer

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


def finish_telemetry(app_container: AppContainer) -> None:
    """Send the spans still batched and stop the exporter (no-op without one)."""

    provider: TracerProvider | None = app_container.utilities.tracer_provider()
    if provider is None:
        return

    try:
        provider.shutdown()
    except Exception as error:  # noqa: BLE001 - shutting down must go on
        LOGGER.warning("Spans could not be sent on shutdown: %s", error)
