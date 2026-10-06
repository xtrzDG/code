"""
One process's metrics page: its own series (or, with
PROMETHEUS_MULTIPROC_DIR, those of every process of the instance) and the
job queue's platform-wide depth, read at scrape time.
"""

from collections.abc import Callable

from app.containers.app import AppContainer
from app.gateways.metrics.job_queue_collector import JobQueueCollector
from app.schemas.configurations.app_settings import AppSettings
from app.utilities.observability.metrics.metrics_exposition import (
    MetricsPage,
    render_metrics,
)


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
