"""
The daily payment reconciliation (`ReconcilePaymentsUseCase`) as a
periodic job of the background worker: once a UTC day one worker compares
the checkout orders of the last week with Flitt and Stripe and keeps the
mismatches for the `payment_mismatch` alert and the admin.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.periodic_job_spec import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

RECONCILE_PAYMENTS_JOB: JobName = JobName("reconcile_payments")
RECONCILE_PAYMENTS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(24 * 60 * 60)


def reconcile_payments_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` once a day."""

    return PeriodicJobSpec(
        name=RECONCILE_PAYMENTS_JOB,
        interval_seconds=RECONCILE_PAYMENTS_INTERVAL,
        operator=operator,
    )
