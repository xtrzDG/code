"""
Threads the API process runs beside its requests: the flush of buffered
model-call traces and, with EMBEDDED_WORKER, the background worker.
"""

import logging
import threading

from app.containers.app import AppContainer
from app.contracts.observability import LlmTraceFacilitatorContract
from app.gateways.worker.background_worker import BackgroundWorker
from app.schemas.configurations.app_settings import AppSettings

LOGGER: logging.Logger = logging.getLogger(__name__)
# Buffered model-call traces of the API process go to Langfuse this often
# (the worker flushes its own buffer as a periodic job).
TRACE_FLUSH_INTERVAL_SECONDS: float = 60.0
# On shutdown the embedded worker gives running jobs time to finish; one
# still running after this long (a long autotest run) is abandoned with a
# warning and runs again once its lease ends.
EMBEDDED_WORKER_STOP_SECONDS: float = 30.0
EMBEDDED_WORKER_THREAD_NAME: str = "embedded-background-worker"


def start_trace_flushing(
    trace_facilitator: LlmTraceFacilitatorContract,
    stop_event: threading.Event,
) -> threading.Thread:
    """Daemon thread that flushes buffered traces until `stop_event` is set."""

    def flush_periodically() -> None:
        while not stop_event.wait(timeout=TRACE_FLUSH_INTERVAL_SECONDS):
            trace_facilitator.flush()

    flush_thread = threading.Thread(
        target=flush_periodically,
        name="llm-trace-flush",
        daemon=True,
    )
    flush_thread.start()
    return flush_thread


def start_embedded_worker(
    app_container: AppContainer,
    stop_event: threading.Event,
) -> threading.Thread | None:
    """
    With EMBEDDED_WORKER, run the background worker (the same periodic jobs
    and job queue as `app.worker_main`) in a daemon thread until
    `stop_event` is set; otherwise nothing is started.
    """

    settings: AppSettings = app_container.config.app_settings()
    if not settings.is_embedded_worker_enabled:
        return None

    worker: BackgroundWorker = app_container.gateways.background_worker()
    worker_thread = threading.Thread(
        target=worker.run_forever,
        args=(stop_event,),
        name=EMBEDDED_WORKER_THREAD_NAME,
        daemon=True,
    )
    worker_thread.start()
    LOGGER.info(
        "Background worker runs inside the API (EMBEDDED_WORKER); without "
        "DATABASE_URL a separate app.worker_main would not see this data"
    )
    return worker_thread


def stop_embedded_worker(worker_thread: threading.Thread) -> None:
    """Wait for the worker's running jobs (its stop event is already set)."""

    worker_thread.join(timeout=EMBEDDED_WORKER_STOP_SECONDS)
    if worker_thread.is_alive():
        LOGGER.warning(
            "Embedded background worker did not finish its tick within %.0f s; "
            "abandoning it",
            EMBEDDED_WORKER_STOP_SECONDS,
        )
        return

    LOGGER.info("Embedded background worker stopped")
