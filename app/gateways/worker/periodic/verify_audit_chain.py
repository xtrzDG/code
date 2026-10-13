"""
Checking the audit log's hash chains, as a periodic job of the background
worker: daily (`VerifyAuditChainsUseCase`).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

VERIFY_AUDIT_CHAIN_JOB: JobName = JobName("verify_audit_chain")
VERIFY_AUDIT_CHAIN_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(24 * 60 * 60)


def verify_audit_chain_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` once a day."""

    return PeriodicJobSpec(
        name=VERIFY_AUDIT_CHAIN_JOB,
        interval_seconds=VERIFY_AUDIT_CHAIN_INTERVAL,
        operator=operator,
    )
