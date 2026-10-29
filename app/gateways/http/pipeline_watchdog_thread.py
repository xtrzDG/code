"""
The API's pipeline watchdog thread: every PIPELINE_WATCHDOG_SECONDS each
API process takes a look (`WatchPipelineUseCase`); the one that leads the
watchdog checks the workers and alerts the team directly. It runs in the
API because the thing it watches, the workers, cannot report their own
absence (docs/operations/runbooks/worker-down.md).
"""

import logging
import threading

from app.containers.app import AppContainer
from app.contracts.operator_contract import OperatorContract
from app.schemas.dto.pipeline_health import PipelineWatchReport, PipelineWatchTick

LOGGER: logging.Logger = logging.getLogger(__name__)
PIPELINE_WATCHDOG_THREAD_NAME: str = "pipeline-watchdog"
# A look holds the alert-state lock for at most 10 s, then sends.
WATCHDOG_STOP_SECONDS: float = 15.0

type WatchOperator = OperatorContract[PipelineWatchTick, PipelineWatchReport]


def watch_until_stopped(
    operator: WatchOperator, interval_seconds: float, stop_event: threading.Event
) -> None:
    """One look per interval until `stop_event` is set; a failed look is logged."""

    while not stop_event.wait(timeout=interval_seconds):
        try:
            report: PipelineWatchReport = operator.operate(PipelineWatchTick())
        except Exception:  # noqa: BLE001 - the watchdog must outlive one bad look
            LOGGER.exception("The pipeline watchdog's look failed")
            continue

        if report.is_leader and int(report.sent_count):
            LOGGER.warning(
                "The pipeline watchdog sent %d alert message(s); the pipeline is %s",
                int(report.sent_count),
                report.pipeline.value if report.pipeline is not None else "unknown",
            )


def start_pipeline_watchdog(
    app_container: AppContainer, stop_event: threading.Event
) -> threading.Thread | None:
    """A daemon thread of looks, or nothing when PIPELINE_WATCHDOG_SECONDS is 0."""

    seconds: int = int(
        app_container.config.app_settings().platform_alerts.watchdog_seconds
    )
    if seconds == 0:
        LOGGER.info("The pipeline watchdog is off (PIPELINE_WATCHDOG_SECONDS=0)")
        return None

    thread = threading.Thread(
        target=watch_until_stopped,
        args=(
            app_container.operators.reliability.watch_pipeline_operator(),
            float(seconds),
            stop_event,
        ),
        name=PIPELINE_WATCHDOG_THREAD_NAME,
        daemon=True,
    )
    thread.start()
    return thread


def stop_pipeline_watchdog(thread: threading.Thread | None) -> None:
    """Wait for a look in progress (the stop event is already set)."""

    if thread is not None:
        thread.join(timeout=WATCHDOG_STOP_SECONDS)
