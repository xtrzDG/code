import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories import (
    AssistantVersionRepoContract,
    AuditLogRepoContract,
    BookingRepoContract,
    BusinessRepoContract,
    CallRepoContract,
    ChannelRepoContract,
    ConversationRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
    UsageEventRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import CallOutcome
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.dto.voice_webhooks import FinishedCallReport, RecordedCall
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.channels.call_outcomes import (
    determine_call_outcome,
    render_call_transcript,
)
from app.utilities.channels.channel_phone_numbers import (
    parse_messaging_phone_number,
)
from app.utilities.channels.voice_recordings import (
    build_voice_platform_recording_path,
)

logger: logging.Logger = logging.getLogger(__name__)


class RecordFinishedCallUseCase(UseCaseContract[FinishedCallReport, RecordedCall]):
    """
    Store a finished phone call in `calls` (concept section 7).

    The business is the owner of the connected phone channel whose number
    was called (the voice agent must be one of that business's agents when
    it has any on record). The call's conversation is the one the voice
    tools opened under the provider call id; what it created gives the
    outcome: booking, lead, handoff, unanswered question, else information
    or an abandoned call. Phone numbers are stored as E.164, the recording
    as a reference to the voice platform's storage, the duration as a
    VOICE_SECONDS usage event with the platform cost. A repeated webhook
    refreshes the stored call without billing it again.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        conversation_repo: ConversationRepoContract,
        call_repo: CallRepoContract,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        handoff_repo: HandoffRepoContract,
        usage_event_repo: UsageEventRepoContract,
        audit_log_repo: AuditLogRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._call_repo: CallRepoContract = call_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: FinishedCallReport) -> RecordedCall:
        assistant_number: E164PhoneNumber | None = (
            None
            if input_data.assistant_number is None
            else parse_messaging_phone_number(
                self._phone_number_parser,
                str(input_data.assistant_number),
            )
        )
        business: BusinessDocument | None = self._find_business(
            assistant_number,
            input_data,
        )
        if business is None:
            return RecordedCall(status=PostCallEventStatus.IGNORED)

        conversation: ConversationDocument | None = self._find_call_conversation(
            business,
            input_data,
        )
        bookings: list[BookingDocument] = self._list_call_bookings(
            business,
            conversation,
        )
        outcome: CallOutcome = determine_call_outcome(
            has_booking=bool(bookings),
            has_lead=self._has_call_lead(business, conversation),
            has_handoff=self._has_call_handoff(business, conversation),
            called_tools=input_data.called_tools,
            transcript=input_data.transcript,
            duration_seconds=int(input_data.duration_seconds),
        )
        now: Microseconds = self._wall_clock.now_unix()
        existing_call: CallDocument | None = self._call_repo.find_by_provider_call_id(
            business.id,
            input_data.provider_call_id,
        )
        call: CallDocument = existing_call or CallDocument(
            business_id=business.id,
            started_at=input_data.started_at,
            provider_call_id=input_data.provider_call_id,
            created_at=now,
            updated_at=now,
        )
        call.conversation_id = None if conversation is None else conversation.id
        call.from_phone_number = (
            None
            if input_data.caller_number is None
            else parse_messaging_phone_number(
                self._phone_number_parser,
                str(input_data.caller_number),
                business.country_code,
            )
        )
        call.to_phone_number = assistant_number
        call.started_at = input_data.started_at
        call.duration_seconds = input_data.duration_seconds
        call.transcript = render_call_transcript(input_data.transcript)
        call.recording_path = (
            build_voice_platform_recording_path(input_data.provider_call_id)
            if input_data.has_recording
            else None
        )
        call.cost_micro_usd = input_data.cost_micro_usd
        call.outcome = outcome
        call.updated_at = now
        self._call_repo.save(call)
        if existing_call is None:
            self._record_usage(call, now)
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    action=AuditAction.CREATE,
                    entity=AuditEntityName("call"),
                    entity_id=AuditEntityReference(str(call.id)),
                    created_at=now,
                    updated_at=now,
                )
            )

        language: LanguageTag = (
            conversation.language
            if conversation is not None and conversation.language is not None
            else input_data.language or business.default_language
        )
        return RecordedCall(
            status=(
                PostCallEventStatus.RECORDED
                if existing_call is None
                else PostCallEventStatus.DUPLICATE
            ),
            business_id=business.id,
            call_id=call.id,
            conversation_id=call.conversation_id,
            contact_id=None if conversation is None else conversation.contact_id,
            outcome=outcome,
            booking_ids=[booking.id for booking in bookings],
            language=language,
        )

    def _find_business(
        self,
        assistant_number: E164PhoneNumber | None,
        report: FinishedCallReport,
    ) -> BusinessDocument | None:
        if assistant_number is None:
            logger.info(
                "Call %s has no assistant number; it is not stored.",
                report.provider_call_id,
            )
            return None

        channel: ChannelDocument | None = self._channel_repo.find_by_external_id(
            ChannelKind.PHONE,
            ChannelExternalId(str(assistant_number)),
        )
        business: BusinessDocument | None = (
            None
            if channel is None or channel.status is not ChannelStatus.CONNECTED
            else self._business_repo.get(channel.business_id)
        )
        if business is None:
            logger.info(
                "Call %s reached a number no business has connected.",
                report.provider_call_id,
            )
            return None

        known_agent_ids = {
            version.voice_agent_id
            for version in self._assistant_version_repo.list_by_business(business.id)
            if version.voice_agent_id is not None
        }
        if (
            report.agent_id is not None
            and known_agent_ids
            and report.agent_id not in known_agent_ids
        ):
            logger.warning(
                "Call %s was answered by an agent of another business; ignored.",
                report.provider_call_id,
            )
            return None

        return business

    def _find_call_conversation(
        self,
        business: BusinessDocument,
        report: FinishedCallReport,
    ) -> ConversationDocument | None:
        call_user_id = ChannelUserId(str(report.provider_call_id))
        for conversation in self._conversation_repo.list_by_business(business.id):
            if (
                conversation.channel is ChannelKind.PHONE
                and conversation.channel_user_id == call_user_id
            ):
                return conversation

        return None

    def _list_call_bookings(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument | None,
    ) -> list[BookingDocument]:
        if conversation is None:
            return []

        bookings: list[BookingDocument] = [
            booking
            for booking in self._booking_repo.list_by_business(business.id)
            if booking.conversation_id == conversation.id
            and booking.status is not BookingStatus.CANCELLED
        ]
        return sorted(bookings, key=lambda booking: booking.created_at)

    def _has_call_lead(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument | None,
    ) -> bool:
        return conversation is not None and any(
            lead.conversation_id == conversation.id
            for lead in self._lead_repo.list_by_business(business.id)
        )

    def _has_call_handoff(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument | None,
    ) -> bool:
        return conversation is not None and any(
            handoff.conversation_id == conversation.id
            for handoff in self._handoff_repo.list_by_business(business.id)
        )

    def _record_usage(self, call: CallDocument, now: Microseconds) -> None:
        self._usage_event_repo.append(
            UsageEventDocument(
                business_id=call.business_id,
                conversation_id=call.conversation_id,
                kind=UsageKind.VOICE_SECONDS,
                quantity=UsageQuantity(int(call.duration_seconds)),
                cost_micro_usd=call.cost_micro_usd,
                occurred_at=call.started_at,
                created_at=now,
                updated_at=now,
            )
        )
