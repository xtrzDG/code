"""The worker sends the text-back of one missed call (WhatsApp, else SMS)."""

import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
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
from app.schemas.constants.deliveries import (
    DeliveryFailureReason,
    OutboundMessageStatus,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.voice.missed_calls.text_back_conversation import (
    open_text_back_conversation,
)
from app.use_cases.voice.missed_calls.text_back_messages import (
    TextBackSettlement,
    TextBackSms,
    is_retryable_failure,
)
from app.use_cases.voice.missed_calls.text_back_rules import is_too_late
from app.use_cases.voice.missed_calls.text_back_whatsapp import TextBackWhatsApp
from app.utilities.calls.text_back_jobs import decode_text_back_payload
from app.utilities.deliveries.retry_policy import describe_delivery_error

LOGGER: logging.Logger = logging.getLogger(__name__)


class SendTextBackUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    Send the message to a caller who did not get through, once.

    WhatsApp: the owner's approved template from the business's number, in
    the caller's language (English when Meta has no such translation), its
    parameter the business name, goes into the outbox (once per missed
    call) and the worker sends it with retries; the outbox runs this job
    again when it was delivered (the missed call is SENT and the WhatsApp
    conversation the caller's reply continues in opens) or refused for
    good (an unknown template, a number without WhatsApp, a broken
    connection): then, when SMS is on, an SMS from the platform's sender
    follows. A temporary SMS failure is tried again by the job queue (the
    last attempt gives up); a message hours late is not queued. Only a
    QUEUED missed call is sent, so a job that runs again sends nothing
    twice.
    """

    def __init__(
        self,
        missed_call_repo: MissedCallRepoContract,
        business_repo: BusinessRepoContract,
        call_settings_repo: CallSettingsRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        whatsapp: TextBackWhatsApp,
        sms: TextBackSms,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._missed_call_repo: MissedCallRepoContract = missed_call_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._call_settings_repo: CallSettingsRepoContract = call_settings_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._whatsapp: TextBackWhatsApp = whatsapp
        self._sms: TextBackSms = sms
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

        caller: E164PhoneNumber = missed.caller_phone_number
        settings: CallSettingsDocument | None = (
            self._call_settings_repo.get_by_business(business.id)
        )
        if missed.channel is TextBackChannel.WHATSAPP:
            missed = self._go_on_whatsapp(business, settings, missed, caller)
            if (
                missed.status is not TextBackStatus.QUEUED
                or missed.channel is TextBackChannel.WHATSAPP
            ):
                return JobReport(processed_count=ProcessedItemCount(1))

        if is_too_late(missed.called_at, self._wall_clock.now_unix()):
            self._settle.skip(missed, TextBackSkipReason.TOO_LATE)
            return JobReport()

        self._try_sms(business, missed, caller, input_data)
        return JobReport(processed_count=ProcessedItemCount(1))

    def _go_on_whatsapp(
        self,
        business: BusinessDocument,
        settings: CallSettingsDocument | None,
        missed: MissedCallDocument,
        caller: E164PhoneNumber,
    ) -> MissedCallDocument:
        """
        The missed call as it goes on: still waiting for WhatsApp (QUEUED
        with the WHATSAPP channel), SENT, switched to SMS or FAILED.
        """

        outbound: OutboundMessageDocument | None = self._whatsapp.queued(missed)
        if outbound is None:
            return self._queue_whatsapp(business, settings, missed, caller)

        if outbound.status is OutboundMessageStatus.PENDING:
            return missed

        if outbound.status is OutboundMessageStatus.DELIVERED:
            return self._delivered(business, missed, caller)

        if outbound.last_failure_reason is DeliveryFailureReason.EXPIRED:
            return self._settle.skip(missed, TextBackSkipReason.TOO_LATE)

        LOGGER.warning(
            "WhatsApp text-back of %s was refused: %s", missed.id, outbound.last_error
        )
        return self._refused(settings, missed, outbound.last_error)

    def _queue_whatsapp(
        self,
        business: BusinessDocument,
        settings: CallSettingsDocument | None,
        missed: MissedCallDocument,
        caller: E164PhoneNumber,
    ) -> MissedCallDocument:
        now: Microseconds = self._wall_clock.now_unix()
        if is_too_late(missed.called_at, now):
            return self._settle.skip(missed, TextBackSkipReason.TOO_LATE)

        template = None if settings is None else settings.text_back_template_name
        try:
            self._whatsapp.queue(business, missed, caller, template, now)
        except ApplicationError as error:
            LOGGER.warning("WhatsApp text-back of %s failed: %s", missed.id, error)
            return self._refused(settings, missed, describe_delivery_error(error))

        return missed

    def _refused(
        self,
        settings: CallSettingsDocument | None,
        missed: MissedCallDocument,
        error: DeliveryErrorText | None,
    ) -> MissedCallDocument:
        if settings is not None and settings.is_sms_fallback_enabled:
            return self._settle.switch_to_sms(missed, error)

        return self._settle.fail(missed, error)

    def _delivered(
        self,
        business: BusinessDocument,
        missed: MissedCallDocument,
        caller: E164PhoneNumber,
    ) -> MissedCallDocument:
        sent: MissedCallDocument = self._settle.sent(missed, TextBackChannel.WHATSAPP)
        conversation_id: ConversationId | None = open_text_back_conversation(
            self._contact_repo,
            self._conversation_repo,
            self._message_repo,
            business,
            caller,
            self._whatsapp.text(business, missed),
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
            self._sms.send(business, missed, caller)
        except ApplicationError as error:
            if is_retryable_failure(error) and not job.is_final_attempt:
                raise

            LOGGER.warning("SMS text-back of %s failed: %s", missed.id, error)
            self._settle.fail(missed, describe_delivery_error(error))
            return

        self._settle.sent(missed, TextBackChannel.SMS)
