"""
The revenue features' periodic jobs of the background worker: a held
waitlist place whose hold ran out goes to the next customer within a
minute (`ExpireWaitlistOffersUseCase`), and the rebooking campaigns write
to the customers their rule finds every hour
(`RunRebookingCampaignsUseCase`). Registered with one line each in the
worker's list of periodic jobs.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

EXPIRE_WAITLIST_OFFERS_JOB: JobName = JobName("expire_waitlist_offers")
EXPIRE_WAITLIST_OFFERS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60)
RUN_REBOOKING_CAMPAIGNS_JOB: JobName = JobName("run_rebooking_campaigns")
RUN_REBOOKING_CAMPAIGNS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60 * 60)


def expire_waitlist_offers_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every minute."""

    return PeriodicJobSpec(
        name=EXPIRE_WAITLIST_OFFERS_JOB,
        interval_seconds=EXPIRE_WAITLIST_OFFERS_INTERVAL,
        operator=operator,
    )


def run_rebooking_campaigns_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=RUN_REBOOKING_CAMPAIGNS_JOB,
        interval_seconds=RUN_REBOOKING_CAMPAIGNS_INTERVAL,
        operator=operator,
    )
