import logging

from app.contracts.facilitators import StaffNotificationSenderContract
from app.contracts.monitoring import DirectPlatformAlertFacilitatorContract
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.monitoring.constrained_integers import NotificationCount
from app.schemas.typings.monitoring.strings import PlatformAlertMessage

logger: logging.Logger = logging.getLogger(__name__)
PLATFORM_TEAM: ManagerName = ManagerName("Platform team")
TEAM_LANGUAGE: LanguageTag = LanguageTag("en")


class DirectPlatformAlertFacilitator(DirectPlatformAlertFacilitatorContract):
    """
    Sends a platform alert to the team straight away, through the platform
    bot's Telegram client and the SMTP client (the staff providers), with
    no job queue in between: the API's pipeline watchdog uses it exactly
    when the workers that drain the queue are gone.

    Every recipient of PLATFORM_ALERT_TELEGRAM_CHAT_IDS and
    PLATFORM_ALERT_EMAILS gets the message in as many parts as its channel
    needs. A recipient that cannot be reached (no provider, a provider
    error) is logged with its channel only and the others still get it;
    the episode's cooldown, not a retry, decides when it is sent again.
    """

    def __init__(
        self,
        staff_sender: StaffNotificationSenderContract,
        alert_settings: PlatformAlertSettings,
    ) -> None:
        self._staff_sender: StaffNotificationSenderContract = staff_sender
        self._settings: PlatformAlertSettings = alert_settings

    def send(self, message: PlatformAlertMessage) -> NotificationCount:
        delivered: int = 0
        for contact in self._recipients():
            try:
                for part in self._staff_sender.split(contact, MessageText(message)):
                    self._staff_sender.send(contact, part, None)
            except ApplicationError as error:
                logger.error(
                    "A platform alert could not go out by %s: %s",
                    contact.channel.value,
                    type(error).__name__,
                )
                continue

            delivered += 1

        return NotificationCount(delivered)

    def _recipients(self) -> list[ManagerContact]:
        addresses: list[tuple[ManagerContactChannel, str]] = [
            (ManagerContactChannel.TELEGRAM, str(chat_id))
            for chat_id in self._settings.telegram_chat_ids
        ] + [
            (ManagerContactChannel.EMAIL, str(email)) for email in self._settings.emails
        ]
        return [
            ManagerContact(
                name=PLATFORM_TEAM,
                channel=channel,
                address=ManagerContactAddress(address),
                language=TEAM_LANGUAGE,
            )
            for channel, address in addresses
        ]
