"""
The sweep of expired rate-limit counters as a periodic job of the
background worker (`SweepRateLimitBucketsUseCase`), every ten minutes:
the counters of a one-minute window are needed for two minutes, those of a
ten-minute window for twenty.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

SWEEP_RATE_LIMIT_BUCKETS_JOB: JobName = JobName("sweep_rate_limit_buckets")
SWEEP_RATE_LIMIT_BUCKETS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(10 * 60)


def sweep_rate_limit_buckets_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every ten minutes."""

    return PeriodicJobSpec(
        name=SWEEP_RATE_LIMIT_BUCKETS_JOB,
        interval_seconds=SWEEP_RATE_LIMIT_BUCKETS_INTERVAL,
        operator=operator,
    )
