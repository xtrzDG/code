"""
The activation follow-up as periodic jobs of the background worker:

- `notice_milestones` every 10 minutes: the first real conversation,
  booking and booking after hours of live businesses, announced to the
  team once (`NoticeMilestonesUseCase`);
- `send_activation_nudges` every hour: the nudge due for each business, at
  most once per business and nudge (`SendActivationNudgesUseCase`; the
  stored nudge is its sent marker).

Both run once per period across every worker (persisted periodic runs).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

NOTICE_MILESTONES_JOB: JobName = JobName("notice_milestones")
NOTICE_MILESTONES_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(10 * 60)
SEND_ACTIVATION_NUDGES_JOB: JobName = JobName("send_activation_nudges")
SEND_ACTIVATION_NUDGES_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60 * 60)


def notice_milestones_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every 10 minutes."""

    return PeriodicJobSpec(
        name=NOTICE_MILESTONES_JOB,
        interval_seconds=NOTICE_MILESTONES_INTERVAL,
        operator=operator,
    )


def send_activation_nudges_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=SEND_ACTIVATION_NUDGES_JOB,
        interval_seconds=SEND_ACTIVATION_NUDGES_INTERVAL,
        operator=operator,
    )
