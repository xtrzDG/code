"""
The sweeper of the inbox as a periodic job of the background worker
(`SweepStaleInboundEventsOrchestrator`), every five minutes: an event whose
job was lost is queued again within minutes of turning stale (twice the
processing lease), and an unanswered customer message reaches a person.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

SWEEP_STALE_INBOUND_EVENTS_JOB: JobName = JobName("sweep_stale_inbound_events")
SWEEP_STALE_INBOUND_EVENTS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(5 * 60)


def sweep_stale_inbound_events_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every five minutes."""

    return PeriodicJobSpec(
        name=SWEEP_STALE_INBOUND_EVENTS_JOB,
        interval_seconds=SWEEP_STALE_INBOUND_EVENTS_INTERVAL,
        operator=operator,
    )
