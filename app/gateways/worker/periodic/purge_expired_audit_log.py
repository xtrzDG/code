"""
The audit and security log's retention as a periodic job of the background
worker: once a day, the entries older than 1,095 days leave every hash
chain (`PurgeExpiredAuditLogUseCase`, PRIV-07). The operator's `workshop
purge-audit-log` stays for a purge by hand.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

PURGE_EXPIRED_AUDIT_LOG_JOB: JobName = JobName("purge_expired_audit_log")
PURGE_EXPIRED_AUDIT_LOG_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(24 * 60 * 60)


def purge_expired_audit_log_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` once a day."""

    return PeriodicJobSpec(
        name=PURGE_EXPIRED_AUDIT_LOG_JOB,
        interval_seconds=PURGE_EXPIRED_AUDIT_LOG_INTERVAL,
        operator=operator,
    )
