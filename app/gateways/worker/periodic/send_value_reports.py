"""
The owners' digests and monthly reports as a periodic job of the
background worker (`SendValueReportsUseCase`), every hour: each business
gets them from 09:00 of its own time zone, once per period across every
worker and restart (the stored report of a period is its sent marker).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

SEND_VALUE_REPORTS_JOB: JobName = JobName("send_value_reports")
SEND_VALUE_REPORTS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60 * 60)


def send_value_reports_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=SEND_VALUE_REPORTS_JOB,
        interval_seconds=SEND_VALUE_REPORTS_INTERVAL,
        operator=operator,
    )
