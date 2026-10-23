"""
Closing and deleting businesses as periodic jobs of the background worker,
across every business (R15-ACCOUNT-DELETION): hourly, the closures whose 30
days are over get their deletion job (`QueueDueDeletionsUseCase`); daily,
businesses whose subscription ended unpaid OFFBOARD_AFTER_DAYS ago are
closed, and those paid again are reopened (`OffboardUnpaidBusinessesUseCase`);
daily, the deletion ledger is applied again, so a database restored from a
backup holds no deleted business (`ReapplyDeletionLedgerUseCase`).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

QUEUE_BUSINESS_DELETIONS_JOB: JobName = JobName("queue_business_deletions")
QUEUE_BUSINESS_DELETIONS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60 * 60)
OFFBOARD_UNPAID_BUSINESSES_JOB: JobName = JobName("offboard_unpaid_businesses")
OFFBOARD_UNPAID_BUSINESSES_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(
    24 * 60 * 60
)


def queue_business_deletions_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The hourly sweep of due closures."""

    return PeriodicJobSpec(
        name=QUEUE_BUSINESS_DELETIONS_JOB,
        interval_seconds=QUEUE_BUSINESS_DELETIONS_INTERVAL,
        operator=operator,
    )


def offboard_unpaid_businesses_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The daily automatic offboarding."""

    return PeriodicJobSpec(
        name=OFFBOARD_UNPAID_BUSINESSES_JOB,
        interval_seconds=OFFBOARD_UNPAID_BUSINESSES_INTERVAL,
        operator=operator,
    )


REAPPLY_DELETION_LEDGER_JOB: JobName = JobName("reapply_deletion_ledger")
REAPPLY_DELETION_LEDGER_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(24 * 60 * 60)


def reapply_deletion_ledger_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The daily ledger, applied again (a restore since the last run)."""

    return PeriodicJobSpec(
        name=REAPPLY_DELETION_LEDGER_JOB,
        interval_seconds=REAPPLY_DELETION_LEDGER_INTERVAL,
        operator=operator,
    )
