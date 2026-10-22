"""
The billing part of the worker's periodic jobs, in the order they run
within a tick: trials end before grace periods are enforced, so an expired
trial and its grace period are handled in the same hour; minutes above the
package and rented phone numbers' months are billed before the grace job
looks for unpaid bills, and seasonal pauses start or end before it looks at
their subscriptions. `periodic_jobs.py` places them in the worker's list.
"""

from dependency_injector.providers import Factory

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.gateways.worker.periodic.phone_number_jobs import (
    bill_phone_number_rentals_job,
)
from app.gateways.worker.periodic.subscription_lifecycle_jobs import (
    run_subscription_pauses_job,
)
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

HOUR_SECONDS: int = 60 * 60
DAY_SECONDS: int = 24 * HOUR_SECONDS

END_TRIALS_JOB: JobName = JobName("end_trials")
ENFORCE_GRACE_PERIODS_JOB: JobName = JobName("enforce_grace_periods")
CHECK_PACKAGE_USAGE_JOB: JobName = JobName("check_package_usage")
INVOICE_USAGE_OVERAGE_JOB: JobName = JobName("invoice_usage_overage")


def billing_job_specs(
    operators: OperatorsContainer,
) -> tuple[Factory[PeriodicJobSpec], ...]:
    """The billing jobs, each run by its operator, in their order."""

    return (
        Factory(
            PeriodicJobSpec,
            name=END_TRIALS_JOB,
            interval_seconds=JobIntervalSeconds(HOUR_SECONDS),
            operator=operators.billing.end_trials_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=INVOICE_USAGE_OVERAGE_JOB,
            interval_seconds=JobIntervalSeconds(HOUR_SECONDS),
            operator=operators.billing.invoice_usage_overage_operator,
        ),
        # Each rented phone number's month (1213).
        Factory(
            bill_phone_number_rentals_job,
            operator=operators.calls.bill_phone_number_rentals_operator,
        ),
        # Seasonal pauses start and end before the grace job (1161).
        Factory(
            run_subscription_pauses_job,
            operator=operators.lifecycle.run_subscription_pauses_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=ENFORCE_GRACE_PERIODS_JOB,
            interval_seconds=JobIntervalSeconds(HOUR_SECONDS),
            operator=operators.billing.enforce_grace_periods_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=CHECK_PACKAGE_USAGE_JOB,
            interval_seconds=JobIntervalSeconds(DAY_SECONDS),
            operator=operators.billing.check_package_usage_operator,
        ),
    )
