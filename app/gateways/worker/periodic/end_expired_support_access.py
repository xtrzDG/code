"""
Ending platform support's expired access as a periodic job of the
background worker: every ten minutes, grants whose time is up are closed
and their end audited (`EndExpiredSupportAccessUseCase`). The access check
refuses an expired grant at once; this job closes the audit trail.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

END_EXPIRED_SUPPORT_ACCESS_JOB: JobName = JobName("end_expired_support_access")
END_EXPIRED_SUPPORT_ACCESS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(10 * 60)


def end_expired_support_access_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every ten minutes."""

    return PeriodicJobSpec(
        name=END_EXPIRED_SUPPORT_ACCESS_JOB,
        interval_seconds=END_EXPIRED_SUPPORT_ACCESS_INTERVAL,
        operator=operator,
    )
