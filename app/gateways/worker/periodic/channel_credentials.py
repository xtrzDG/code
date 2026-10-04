"""
The hourly check of Meta channel tokens (`CheckChannelCredentialsUseCase`):
each WhatsApp, Instagram and Messenger token is asked about once a day
with the platform's Meta app (META_APP_ID, META_APP_SECRET), and the admin
system page lists those that run out within two weeks.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

CHECK_CHANNEL_CREDENTIALS_JOB: JobName = JobName("check_channel_credentials")
CHECK_CHANNEL_CREDENTIALS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60 * 60)


def check_channel_credentials_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=CHECK_CHANNEL_CREDENTIALS_JOB,
        interval_seconds=CHECK_CHANNEL_CREDENTIALS_INTERVAL,
        operator=operator,
    )
