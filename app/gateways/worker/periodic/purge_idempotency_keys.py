"""
Deleting the idempotency keys of creating requests whose day ran out (and
those a failed request released), as a periodic job of the background
worker: hourly (`PurgeIdempotencyKeysUseCase`).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

PURGE_IDEMPOTENCY_KEYS_JOB: JobName = JobName("purge_idempotency_keys")
PURGE_IDEMPOTENCY_KEYS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60 * 60)


def purge_idempotency_keys_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=PURGE_IDEMPOTENCY_KEYS_JOB,
        interval_seconds=PURGE_IDEMPOTENCY_KEYS_INTERVAL,
        operator=operator,
    )
