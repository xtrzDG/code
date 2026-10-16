import hashlib
import logging

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.spend_guard import SpendLimitNoticeFacilitatorContract
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.platform_alerts import PlatformAlertDelivery
from app.schemas.dto.spend_guard import SpendLimitPassing
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.monitoring.strings import PlatformAlertMessage
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.spend.spend_notice_texts import (
    OWNER_NOTICES,
    TEAM_NOTICES,
    fill_notice,
)

logger: logging.Logger = logging.getLogger(__name__)
# The platform alerts' job (`SendPlatformAlertUseCase`): one message to
# one recipient of the team, retried with backoff by the job queue.
SEND_PLATFORM_ALERT_JOB: JobName = JobName("send_platform_alert")


class SpendLimitNoticeFacilitator(SpendLimitNoticeFacilitatorContract):
    """
    Tells a business's owners and the platform team, once, that it passed a
    daily spend limit: each owner through the staff outbox (their sign-in
    e-mail or phone, in their language), the team as `send_platform_alert`
    jobs to the platform alert recipients (PLATFORM_ALERT_*), in the
    outbound lane. Queuing never raises: a failure is logged and the turn
    goes on.
    """

    def __init__(
        self,
        manager_notifier: ManagerNotificationFacilitatorContract,
        job_queue: JobQueueFacilitatorContract,
        localized_text_resolver: LocalizedTextResolverContract,
        alert_settings: PlatformAlertSettings,
    ) -> None:
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._alert_settings: PlatformAlertSettings = alert_settings

    def announce(
        self, passing: SpendLimitPassing, owners: list[ManagerContact]
    ) -> None:
        owner_notice = OWNER_NOTICES.get(passing.level)
        if owner_notice is not None:
            for owner in owners:
                text = MessageText(
                    fill_notice(
                        str(self._resolver.resolve(owner_notice, owner.language)),
                        passing,
                    )
                )
                self._manager_notifier.notify(
                    StaffNotification(
                        business_id=passing.business.id, contact=owner, text=text
                    )
                )

        team_notice = TEAM_NOTICES.get(passing.level)
        if team_notice is None:
            return

        message = PlatformAlertMessage(fill_notice(team_notice, passing))
        for channel, address in self._team_recipients():
            try:
                self._job_queue.enqueue(
                    SEND_PLATFORM_ALERT_JOB,
                    JobPayloadJson(
                        PlatformAlertDelivery(
                            channel=channel,
                            address=ManagerContactAddress(address),
                            text=message,
                        ).model_dump_json()
                    ),
                    None,
                    lane=JobLane.OUTBOUND,
                    serial_key=team_serial_key(channel, address),
                )
            except ApplicationError:
                logger.exception("A spend limit notice for the team was not queued.")

    def _team_recipients(self) -> list[tuple[ManagerContactChannel, str]]:
        return [
            (ManagerContactChannel.TELEGRAM, str(chat_id))
            for chat_id in self._alert_settings.telegram_chat_ids
        ] + [
            (ManagerContactChannel.EMAIL, str(email))
            for email in self._alert_settings.emails
        ]


def team_serial_key(channel: ManagerContactChannel, address: str) -> JobSerialKey:
    """
    The same serial key as the platform alerts' (a digest of the address,
    not it), so one recipient's alerts and spend notices go out in order.
    """

    digest: str = hashlib.sha256(f"{channel.value}:{address}".encode()).hexdigest()
    return JobSerialKey(f"platform_alert:{digest[:16]}")
