"""
The daily digest of clients that newly turned critical
(`SendCriticalClientsDigestUseCase`), a periodic job of the background
worker once a day across workers: the clients go to the platform team's
Telegram chats through the platform bot (PLATFORM_ALERT_TELEGRAM_CHAT_IDS)
by way of the queue (`send_platform_alert`).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

CRITICAL_CLIENTS_DIGEST_JOB: JobName = JobName("critical_clients_digest")
CRITICAL_CLIENTS_DIGEST_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(24 * 60 * 60)


def critical_clients_digest_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` once a day."""

    return PeriodicJobSpec(
        name=CRITICAL_CLIENTS_DIGEST_JOB,
        interval_seconds=CRITICAL_CLIENTS_DIGEST_INTERVAL,
        operator=operator,
    )
