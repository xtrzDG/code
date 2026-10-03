"""The worker sends the text-back of one missed call (WhatsApp, else SMS)."""

import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.messaging_clients import SmsMessagingClientContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.call_follow_up_repositories import (
    CallSettingsRepoContract,
    MissedCallRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.calls import (
    TextBackChannel,
    TextBackSkipReason,
    TextBackStatus,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.voice.missed_calls.text_back_conversation import (
    open_text_back_conversation,
)
from app.use_cases.voice.missed_calls.text_back_messages import (
    TextBackSender,
    TextBackSettlement,
    is_retryable_failure,
)
from app.use_cases.voice.missed_calls.text_back_rules import is_too_late
from app.utilities.calls.text_back_jobs import decode_text_back_payload

LOGGER: logging.Logger = logging.getLogger(__name__)


class SendTextBackUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    Send the message to a caller who did not get through, once.

    WhatsApp: the owner's approved template from the business's number, in
    the caller's language (English when Meta has no such translation), its
    parameter the business name; the message then opens the WhatsApp
    conversation the caller's reply continues in. When WhatsApp refuses
    the message for good (an unknown template, a number without WhatsApp,
    a broken connection) and SMS is on, an SMS from the platform's sender
    follows. A temporary failure is tried again by the job queue (the last
    attempt gives up); a message hours late is not sent. Only a QUEUED
    missed call is sent, so a job that runs again sends nothing twice.
    """

    def __init__(
        self,
        missed_call_repo: MissedCallRepoContract,
        business_repo: BusinessRepoContract,
        call_settings_repo: CallSettingsRepoContract,
        channel_repo: ChannelRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        channel_message_sender: ChannelMessageSenderFacilitatorContract,
        sms_client: SmsMessagingClientContract | None,
        text_resolver: LocalizedTextResolverContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._missed_call_repo: MissedCallRepoContract = missed_call_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._call_settings_repo: CallSettingsRepoContract = call_settings_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._sender: TextBackSender = TextBackSender(
            channel_repo, channel_message_sender, sms_client, text_resolver
        )
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._settle: TextBackSettlement = TextBackSettlement(
            missed_call_repo, wall_clock
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        missed_call_id: MissedCallId = decode_text_back_payload(input_data.payload)
        if input_data.business_id is None:
            return JobReport()

        missed: MissedCallDocument | None = self._missed_call_repo.get(
            input_data.business_id, missed_call_id
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if (
            missed is None
            or missed.status is not TextBackStatus.QUEUED
            or business is None
            or missed.caller_phone_number is None
        ):
            return JobReport()

        if is_too_late(missed.called_at, self._wall_clock.now_unix()):
            self._settle.skip(missed, TextBackSkipReason.TOO_LATE)
            return JobReport()

        settings: CallSettingsDocument | None = (
            self._call_settings_repo.get_by_business(business.id)
        )
        caller: E164PhoneNumber = missed.caller_phone_number
        if missed.channel is TextBackChannel.WHATSAPP:
            missed = self._try_whatsapp(business, settings, missed, caller, input_data)
            if missed.status is not TextBackStatus.QUEUED:
                return JobReport(processed_count=ProcessedItemCount(1))

        self._try_sms(business, missed, caller, input_data)
        return JobReport(processed_count=ProcessedItemCount(1))

    def _try_whatsapp(
        self,
        business: BusinessDocument,
        settings: CallSettingsDocument | None,
        missed: MissedCallDocument,
        caller: E164PhoneNumber,
        job: QueuedJobInput,
    ) -> MissedCallDocument:
        """Sent (SENT), or the missed call as it should go on (SMS or FAILED)."""

        template = None if settings is None else settings.text_back_template_name
        try:
            text = self._sender.send_whatsapp(business, missed, caller, template)
        except ApplicationError as error:
            if is_retryable_failure(error) and not job.is_final_attempt:
                raise

            LOGGER.warning("WhatsApp text-back of %s failed: %s", missed.id, error)
            if settings is not None and settings.is_sms_fallback_enabled:
                return self._settle.switch_to_sms(missed, error)

            return self._settle.fail(missed, error)

        sent: MissedCallDocument = self._settle.sent(missed, TextBackChannel.WHATSAPP)
        conversation_id: ConversationId | None = open_text_back_conversation(
            self._contact_repo,
            self._conversation_repo,
            self._message_repo,
            business,
            caller,
            text,
            missed.language,
            self._wall_clock.now_unix(),
        )
        if conversation_id is not None:
            self._live_events.publish(
                business.id, LiveEventKind.CONVERSATION_MESSAGE, (conversation_id,)
            )
            sent = self._settle.link(sent, conversation_id)

        return sent

    def _try_sms(
        self,
        business: BusinessDocument,
        missed: MissedCallDocument,
        caller: E164PhoneNumber,
        job: QueuedJobInput,
    ) -> None:
        try:
            self._sender.send_sms(business, missed, caller)
        except ApplicationError as error:
            if is_retryable_failure(error) and not job.is_final_attempt:
                raise

            LOGGER.warning("SMS text-back of %s failed: %s", missed.id, error)
            self._settle.fail(missed, error)
            return

        self._settle.sent(missed, TextBackChannel.SMS)
