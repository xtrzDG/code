"""
The sub-processor change notices as a periodic job of the background
worker, once a day (`SendSubprocessorNoticesUseCase`): owners hear of an
addition or a removal the notice period (DPA 8.3, 30 days) before it takes
effect. The days count in UTC, so a daily run is in time.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

SEND_SUBPROCESSOR_NOTICES_JOB: JobName = JobName("send_subprocessor_notices")
SEND_SUBPROCESSOR_NOTICES_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(
    24 * 60 * 60
)


def send_subprocessor_notices_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` once a day."""

    return PeriodicJobSpec(
        name=SEND_SUBPROCESSOR_NOTICES_JOB,
        interval_seconds=SEND_SUBPROCESSOR_NOTICES_INTERVAL,
        operator=operator,
    )
