"""
The subscription lifecycle's periodic jobs of the background worker:
seasonal pauses start, bill their months and resume every hour, before the
grace job looks at the same subscriptions (`RunSubscriptionPausesUseCase`);
win-back messages go out every hour, in each business's daytime
(`SendWinBackMessagesUseCase`). Registered with one line each in the
worker's list of periodic jobs.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

RUN_SUBSCRIPTION_PAUSES_JOB: JobName = JobName("run_subscription_pauses")
SEND_WIN_BACK_MESSAGES_JOB: JobName = JobName("send_win_back_messages")
HOURLY: JobIntervalSeconds = JobIntervalSeconds(60 * 60)


def run_subscription_pauses_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=RUN_SUBSCRIPTION_PAUSES_JOB, interval_seconds=HOURLY, operator=operator
    )


def send_win_back_messages_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=SEND_WIN_BACK_MESSAGES_JOB, interval_seconds=HOURLY, operator=operator
    )
