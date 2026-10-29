from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channel_events import PlatformBotCommandResult
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.channels.staff_links import (
    PlatformBotWebhookOutcome,
    PlatformBotWebhookRequest,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    NotFoundError,
)
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.deliveries.strings import InboundPayloadText
from app.schemas.typings.platform.strings import PlatformSecret
from app.use_cases.shared.inbox_queue import store_and_queue
from app.utilities.channels.platform_bot_updates import (
    StaffBotMessage,
    read_staff_bot_message,
)
from app.utilities.channels.webhook_signatures import is_matching_telegram_secret
from app.utilities.deliveries.delivery_jobs import PROCESS_PLATFORM_BOT_UPDATE_JOB
from app.utilities.deliveries.delivery_keys import (
    bounded_provider_message_id,
    derive_inbound_event_id,
    inbound_serial_key,
)
from app.utilities.security.key_ring import key_ring


class AcceptPlatformBotUpdateUseCase(
    UseCaseContract[PlatformBotWebhookRequest, PlatformBotWebhookOutcome]
):
    """
    Webhook of the platform Telegram bot that notifies staff, acknowledged
    at once: check the secret token derived from the bot token, keep a
    staff message in the inbox and queue `process_platform_bot_update` (the
    worker links the chat and answers). Other updates, and a message
    Telegram delivered before, are ignored.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        job_queue: JobQueueFacilitatorContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        unit_of_work: StorageUnitOfWorkContract | None = None,
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work

    def run(self, input_data: PlatformBotWebhookRequest) -> PlatformBotWebhookOutcome:
        self._authenticate(input_data)
        message: StaffBotMessage | None = read_staff_bot_message(
            input_data.payload.body
        )
        payload: InboundPayloadText | None = read_payload_text(input_data.payload.body)
        if message is None or payload is None:
            return PlatformBotWebhookOutcome(result=PlatformBotCommandResult.IGNORED)

        now: Microseconds = self._wall_clock.now_unix()
        provider_message_id: ProviderMessageId = bounded_provider_message_id(
            message.update_id
        )
        event = InboundEventDocument(
            id=derive_inbound_event_id(None, ChannelKind.TELEGRAM, provider_message_id),
            kind=InboundEventKind.PLATFORM_BOT_UPDATE,
            channel=ChannelKind.TELEGRAM,
            provider_message_id=provider_message_id,
            payload=payload,
            created_at=now,
            updated_at=now,
        )
        is_new: bool = store_and_queue(
            self._inbound_event_repo,
            self._job_queue,
            event,
            PROCESS_PLATFORM_BOT_UPDATE_JOB,
            inbound_serial_key(None, ChannelKind.TELEGRAM, str(message.chat_id)),
            unit_of_work=self._unit_of_work,
        )
        return PlatformBotWebhookOutcome(
            result=(
                PlatformBotCommandResult.QUEUED
                if is_new
                else PlatformBotCommandResult.IGNORED
            )
        )

    def _authenticate(self, input_data: PlatformBotWebhookRequest) -> None:
        bot_token: PlatformSecret | None = (
            self._app_settings.telegram_platform_bot_token
        )
        keys: list[PlatformSecret] = key_ring(self._app_settings)
        if bot_token is None or not keys:
            raise NotFoundError("The platform bot is not configured.")

        if not is_matching_telegram_secret(
            keys, bot_token, input_data.payload.signature_header
        ):
            raise AuthenticationRequiredError(
                "The Telegram webhook secret token is missing or wrong."
            )


def read_payload_text(body: bytes) -> InboundPayloadText | None:
    """The body as text for the inbox; None when it is not UTF-8."""

    try:
        return InboundPayloadText(body.decode("utf-8"))
    except UnicodeDecodeError:
        return None
