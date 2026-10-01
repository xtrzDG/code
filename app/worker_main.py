"""
Background worker entry point:

    uv run python -m app.worker_main

Runs the periodic jobs (retention purge, trials and grace periods, package
usage, booking reminders, trace flush) and drains the job queue until
SIGINT or SIGTERM; the current tick finishes before the process exits.
"""

import logging
import signal
import threading
from types import FrameType

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.containers.app import AppContainer
from app.gateways.worker.background_worker import BackgroundWorker

LOGGER: logging.Logger = logging.getLogger(__name__)
STOP_SIGNALS: tuple[signal.Signals, ...] = (signal.SIGINT, signal.SIGTERM)


def main(
    app_container: AppContainer | None = None,
    stop_event: threading.Event | None = None,
) -> int:
    """Run the worker until stopped; returns the process exit code."""

    container: AppContainer = AppContainer() if app_container is None else app_container
    stop: threading.Event = threading.Event() if stop_event is None else stop_event
    install_stop_signal_handlers(stop)
    worker: BackgroundWorker = container.gateways.background_worker()
    LOGGER.info("Background worker started")
    try:
        worker.run_forever(stop)
    finally:
        shut_down(container)

    LOGGER.info("Background worker stopped")
    return 0


def install_stop_signal_handlers(stop_event: threading.Event) -> None:
    """SIGINT and SIGTERM ask the worker to stop after the current tick."""

    if threading.current_thread() is not threading.main_thread():
        return

    def request_stop(signal_number: int, frame: FrameType | None) -> None:
        del frame
        LOGGER.info("Signal %d received; stopping after this tick", signal_number)
        stop_event.set()

    for stop_signal in STOP_SIGNALS:
        signal.signal(stop_signal, request_stop)


def shut_down(app_container: AppContainer) -> None:
    """Send the remaining traces and close the Postgres pool."""

    app_container.adapters.llm_trace_facilitator().flush()
    connection_pool: PostgresConnectionPoolClient | None = (
        app_container.clients.postgres_pool()
    )
    if connection_pool is not None:
        connection_pool.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    raise SystemExit(main())
