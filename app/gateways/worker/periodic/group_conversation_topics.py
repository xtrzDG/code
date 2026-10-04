"""
What customers ask about as a periodic job of the background worker
(`GroupConversationTopicsUseCase`), every hour: each business's topics are
grouped once a night of its own time zone (03:00 to 09:00), a business
never grouped at once; the stored document's window is its done marker.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

GROUP_CONVERSATION_TOPICS_JOB: JobName = JobName("group_conversation_topics")
GROUP_CONVERSATION_TOPICS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60 * 60)


def group_conversation_topics_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=GROUP_CONVERSATION_TOPICS_JOB,
        interval_seconds=GROUP_CONVERSATION_TOPICS_INTERVAL,
        operator=operator,
    )
