"""
The periodic jobs of Meta channel tokens, both with the platform's Meta app
(META_APP_ID, META_APP_SECRET):

- the hourly check (`CheckChannelCredentialsUseCase`): each WhatsApp,
  Instagram and Messenger token is asked about once a day, and the admin
  system page lists those that run out within two weeks;
- the renewal of Embedded Signup's WhatsApp tokens every 6 hours
  (`RefreshWhatsAppTokensUseCase`): a token whose end the check stored
  within META_TOKEN_REFRESH_DAYS is renewed, and the owners are told when
  Meta refuses or the token ends.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

CHECK_CHANNEL_CREDENTIALS_JOB: JobName = JobName("check_channel_credentials")
CHECK_CHANNEL_CREDENTIALS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60 * 60)
REFRESH_WHATSAPP_TOKENS_JOB: JobName = JobName("refresh_whatsapp_tokens")
REFRESH_WHATSAPP_TOKENS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(6 * 60 * 60)


def check_channel_credentials_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=CHECK_CHANNEL_CREDENTIALS_JOB,
        interval_seconds=CHECK_CHANNEL_CREDENTIALS_INTERVAL,
        operator=operator,
    )


def refresh_whatsapp_tokens_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """
    The periodic job spec that runs `operator` every 6 hours, on the
    default lane (the batch worker).
    """

    return PeriodicJobSpec(
        name=REFRESH_WHATSAPP_TOKENS_JOB,
        interval_seconds=REFRESH_WHATSAPP_TOKENS_INTERVAL,
        operator=operator,
    )
