"""
Series read from the database at scrape time, so every API instance and
worker reports the same, platform-wide figures: the job queue's depth and
age per lane and the dead letters per job.
"""

import logging
from collections.abc import Iterable

from prometheus_client.metrics_core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector

from app.contracts.operator_contract import OperatorContract
from app.schemas.dto.telemetry import JobQueueMeasurement, JobQueueQuery
from app.schemas.exceptions.base_exception import ApplicationError

LOGGER: logging.Logger = logging.getLogger(__name__)


class JobQueueCollector(Collector):
    """
    One measurement per scrape. When the database cannot answer, the queue
    series are left out of that scrape (Prometheus marks them stale) and
    the other series are still served.
    """

    def __init__(
        self,
        measure_operator: OperatorContract[JobQueueQuery, JobQueueMeasurement],
    ) -> None:
        self._measure: OperatorContract[JobQueueQuery, JobQueueMeasurement] = (
            measure_operator
        )

    def collect(self) -> Iterable[Metric]:
        try:
            measurement: JobQueueMeasurement = self._measure.operate(JobQueueQuery())
        except ApplicationError as error:
            LOGGER.warning("The job queue could not be measured: %s", error)
            return []

        due = GaugeMetricFamily(
            "workshop_queue_due_jobs",
            "Queued jobs due now and not yet taken by a worker, by lane.",
            labels=["lane"],
        )
        oldest = GaugeMetricFamily(
            "workshop_queue_oldest_wait_seconds",
            "How long the oldest due job of the lane has waited (0: none due).",
            labels=["lane"],
        )
        dead = GaugeMetricFamily(
            "workshop_dead_jobs",
            "Dead letters of the job queue by job name.",
            labels=["job"],
        )
        for lane in measurement.lanes:
            due.add_metric([lane.lane.value], float(int(lane.due_jobs)))
            wait: int = (
                0 if lane.oldest_wait_seconds is None else int(lane.oldest_wait_seconds)
            )
            oldest.add_metric([lane.lane.value], float(wait))
        for tally in measurement.dead_jobs:
            dead.add_metric([str(tally.name)], float(int(tally.count)))

        return [due, oldest, dead]
