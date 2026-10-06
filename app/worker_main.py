"""
Background worker entry point:

    uv run python -m app.worker_main

Runs the periodic jobs (retention purge, trials and grace periods, package
usage, booking reminders, purge of finished jobs, trace flush) once per
period, and the queued jobs of every lane on their own threads, until SIGINT
or SIGTERM. Any number of workers may run side by side (leased claims). On
stop, running jobs get up to 25 seconds; a job cut off then runs again on
another worker once its lease ends. With WORKER_METRICS_PORT and
METRICS_TOKEN it serves its metrics (docs/operations/observability.md).
"""

import logging
import signal
import threading
from types import FrameType

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.containers.app import AppContainer
from app.gateways.metrics.metrics_rendering import start_worker_metrics
from app.gateways.metrics.worker_metrics_server import WorkerMetricsServer
from app.gateways.startup_checks import check_processor_uses
from app.gateways.telemetry_lifecycle import (
    WORKER_SERVICE_NAME,
    finish_telemetry,
    name_service,
)
from app.gateways.worker.background_worker import BackgroundWorker
from app.utilities.observability.logging_setup import configure_logging

LOGGER: logging.Logger = logging.getLogger(__name__)
STOP_SIGNALS: tuple[signal.Signals, ...] = (signal.SIGINT, signal.SIGTERM)


def main(
    app_container: AppContainer | None = None,
    stop_event: threading.Event | None = None,
) -> int:
    """
    Run the worker until stopped; returns the process exit code. A flow of
    personal data to a provider the sub-processor list does not cover stops
    it in production before it starts (`check_processor_uses`).
    """

    container: AppContainer = AppContainer() if app_container is None else app_container
    stop: threading.Event = threading.Event() if stop_event is None else stop_event
    install_stop_signal_handlers(stop)
    # The worker sends the nightly quality sample: it checks the providers too.
    check_processor_uses(container)
    worker: BackgroundWorker = container.gateways.background_worker()
    metrics_server: WorkerMetricsServer | None = start_worker_metrics(container)
    LOGGER.info("Background worker started")
    try:
        worker.run_forever(stop)
    finally:
        if metrics_server is not None:
            metrics_server.stop()
        shut_down(container)

    LOGGER.info("Background worker stopped")
    return 0


def install_stop_signal_handlers(stop_event: threading.Event) -> None:
    """SIGINT and SIGTERM ask the worker to stop (running jobs may finish)."""

    if threading.current_thread() is not threading.main_thread():
        return

    def request_stop(signal_number: int, frame: FrameType | None) -> None:
        del frame
        LOGGER.info("Signal %d received; stopping the worker", signal_number)
        stop_event.set()

    for stop_signal in STOP_SIGNALS:
        signal.signal(stop_signal, request_stop)


def shut_down(app_container: AppContainer) -> None:
    """Send the remaining traces and spans, close the Postgres pool."""

    app_container.adapters.llm_trace_facilitator().flush()
    finish_telemetry(app_container)
    connection_pool: PostgresConnectionPoolClient | None = (
        app_container.clients.postgres_pool()
    )
    if connection_pool is not None:
        connection_pool.close()


def run_from_environment() -> int:
    """`python -m app.worker_main`: settings and logging from the environment."""

    name_service(WORKER_SERVICE_NAME)
    app_container = AppContainer()
    configure_logging(app_container.config.app_settings().log_format)
    return main(app_container)


if __name__ == "__main__":
    raise SystemExit(run_from_environment())
