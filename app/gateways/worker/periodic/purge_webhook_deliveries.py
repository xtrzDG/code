"""
Deleting the outbound webhooks' delivery log past its 30 days, as a periodic
job of the background worker: daily (`PurgeWebhookDeliveriesUseCase`).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

PURGE_WEBHOOK_DELIVERIES_JOB: JobName = JobName("purge_webhook_deliveries")
PURGE_WEBHOOK_DELIVERIES_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(86_400)


def purge_webhook_deliveries_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` once a day."""

    return PeriodicJobSpec(
        name=PURGE_WEBHOOK_DELIVERIES_JOB,
        interval_seconds=PURGE_WEBHOOK_DELIVERIES_INTERVAL,
        operator=operator,
    )
