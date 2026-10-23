"""The worker's periodic jobs of closing and deleting businesses (1220)."""

from dependency_injector.providers import Factory, Provider

from app.containers.account_deletion.account_deletion_operator_factories import (
    AccountDeletionOperatorFactories,
)
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.gateways.worker.periodic.business_closure_jobs import (
    offboard_unpaid_businesses_job,
    queue_business_deletions_job,
    reapply_deletion_ledger_job,
)


def closure_periodic_job_specs(
    account_deletions: Provider[AccountDeletionOperatorFactories],
) -> list[Factory[PeriodicJobSpec]]:
    """
    Closed businesses deleted when due (hourly), unpaid ones closed and the
    deletion ledger applied again after a restore (daily; 1220).
    """

    return [
        Factory(
            queue_business_deletions_job,
            operator=Factory(
                AccountDeletionOperatorFactories.queue_due_deletions, account_deletions
            ),
        ),
        Factory(
            offboard_unpaid_businesses_job,
            operator=Factory(
                AccountDeletionOperatorFactories.offboard_unpaid_businesses,
                account_deletions,
            ),
        ),
        Factory(
            reapply_deletion_ledger_job,
            operator=Factory(
                AccountDeletionOperatorFactories.reapply_deletion_ledger,
                account_deletions,
            ),
        ),
    ]
