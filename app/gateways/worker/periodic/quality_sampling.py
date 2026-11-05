"""
Production quality as a periodic job of the background worker
(`SampleConversationQualityUseCase`), once a day across workers: the judge
scores a small, cost-capped sample of the day's real conversations.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

QUALITY_SAMPLING_JOB: JobName = JobName("sample_conversation_quality")
QUALITY_SAMPLING_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(24 * 60 * 60)


def quality_sampling_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` once a day."""

    return PeriodicJobSpec(
        name=QUALITY_SAMPLING_JOB,
        interval_seconds=QUALITY_SAMPLING_INTERVAL,
        operator=operator,
    )
