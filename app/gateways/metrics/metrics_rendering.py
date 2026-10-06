"""
One process's metrics page: its own series (or, with
PROMETHEUS_MULTIPROC_DIR, those of every process of the instance) and, on
the API, the job queue's platform-wide depth, read at scrape time. A worker
serves its own series on WORKER_METRICS_PORT when it and METRICS_TOKEN are
set.
"""

import logging
from collections.abc import Callable

from app.containers.app import AppContainer
from app.gateways.metrics.job_queue_collector import JobQueueCollector
from app.gateways.metrics.worker_metrics_server import WorkerMetricsServer
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.configurations.telemetry_settings import TelemetrySettings
from app.utilities.observability.metrics.metrics_exposition import (
    MetricsPage,
    render_metrics,
)

LOGGER: logging.Logger = logging.getLogger(__name__)


def metrics_renderer(app_container: AppContainer) -> Callable[[], MetricsPage]:
    """What GET /metrics and the worker's metrics port answer, per scrape."""

    settings: AppSettings = app_container.config.app_settings()
    queue_collector = JobQueueCollector(
        app_container.operators.telemetry.measure_job_queues_operator()
    )

    def render() -> MetricsPage:
        return render_metrics(
            app_container.utilities.metrics_registry(),
            settings.telemetry.prometheus_multiproc_directory,
            [queue_collector],
        )

    return render


def start_worker_metrics(app_container: AppContainer) -> WorkerMetricsServer | None:
    """
    The worker's metrics page, started, when WORKER_METRICS_PORT and
    METRICS_TOKEN are both set (the queue's depth is on the API's page).
    """

    settings: TelemetrySettings = app_container.config.app_settings().telemetry
    if settings.worker_metrics_port is None:
        return None

    if settings.metrics_token is None:
        LOGGER.warning(
            "WORKER_METRICS_PORT is set without METRICS_TOKEN; "
            "the worker serves no metrics."
        )
        return None

    def render() -> MetricsPage:
        return render_metrics(
            app_container.utilities.metrics_registry(),
            settings.prometheus_multiproc_directory,
        )

    server = WorkerMetricsServer(
        settings.worker_metrics_port, settings.metrics_token, render
    )
    server.start()
    return server
