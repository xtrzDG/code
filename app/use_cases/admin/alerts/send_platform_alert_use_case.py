import logging

from app.contracts.facilitators import StaffNotificationSenderContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.platform_alerts import PlatformAlertDelivery
from app.schemas.exceptions.application_errors import DeliveryNotConfiguredError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount

logger: logging.Logger = logging.getLogger(__name__)
PLATFORM_TEAM: ManagerName = ManagerName("Platform team")
TEAM_LANGUAGE: LanguageTag = LanguageTag("en")


class SendPlatformAlertUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    A `send_platform_alert` job: one platform alert message to one
    recipient of the team, through the platform's staff providers (a
    Telegram chat through the platform bot, e-mail over SMTP), in as many
    platform messages as the channel needs.

    A provider failure raises, so the job queue retries with backoff and
    keeps the message as a dead letter when it never gets through. A
    channel without a provider (no platform bot token, no SMTP) cannot
    succeed by retrying: it is logged and the job ends.
    """

    def __init__(self, staff_sender: StaffNotificationSenderContract) -> None:
        self._staff_sender: StaffNotificationSenderContract = staff_sender

    def run(self, input_data: QueuedJobInput) -> JobReport:
        delivery = PlatformAlertDelivery.model_validate_json(str(input_data.payload))
        contact = ManagerContact(
            name=PLATFORM_TEAM,
            channel=delivery.channel,
            address=delivery.address,
            language=TEAM_LANGUAGE,
        )
        parts: list[MessageText] = self._staff_sender.split(
            contact, MessageText(str(delivery.text))
        )
        try:
            for part in parts:
                self._staff_sender.send(contact, part, None)
        except DeliveryNotConfiguredError as error:
            logger.warning(
                "A platform alert could not go out by %s: %s",
                delivery.channel.value,
                error,
            )
            return JobReport()

        return JobReport(processed_count=ProcessedItemCount(len(parts)))
