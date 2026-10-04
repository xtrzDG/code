"""Store a finished phone call reported by the voice platform."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import CallOutcome
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.dto.voice_webhooks import FinishedCallReport, RecordedCall
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.use_cases.voice.finished_call.call_activity import (
    find_call_conversation,
    has_call_handoff,
    has_call_lead,
    list_call_bookings,
)
from app.use_cases.voice.finished_call.call_business_lookup import find_call_business
from app.use_cases.voice.finished_call.call_usage_events import (
    build_transfer_usage_event,
    build_voice_usage_event,
)
from app.utilities.channels.call_outcomes import (
    determine_call_outcome,
    render_call_transcript,
)
from app.utilities.channels.channel_phone_numbers import parse_messaging_phone_number
from app.utilities.channels.voice_recordings import build_voice_platform_recording_path
from app.utilities.sharing.acquisition_sources import called_number_source


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
        business: BusinessDocument | None = find_call_business(
            self._channel_repo,
            self._business_repo,
            self._assistant_version_repo,
            assistant_number,
            input_data,
        )
        if business is None:
            return RecordedCall(status=PostCallEventStatus.IGNORED)

        conversation: ConversationDocument | None = find_call_conversation(
            self._conversation_repo,
            business,
            input_data,
        )
        self._keep_called_number(conversation, assistant_number)
        bookings: list[BookingDocument] = list_call_bookings(
            self._booking_repo,
            business,
            conversation,
        )
        outcome: CallOutcome = determine_call_outcome(
            has_booking=bool(bookings),
            has_lead=has_call_lead(self._lead_repo, business, conversation),
            has_handoff=has_call_handoff(self._handoff_repo, business, conversation),
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
            self._usage_event_repo.append(build_voice_usage_event(call, now))
            transfer_event: UsageEventDocument | None = build_transfer_usage_event(
                call, input_data, now
            )
            if transfer_event is not None:
                self._usage_event_repo.append(transfer_event)

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

    def _keep_called_number(
        self,
        conversation: ConversationDocument | None,
        assistant_number: E164PhoneNumber | None,
    ) -> None:
        """A call's conversation (opened by a tool) comes from the line dialled."""

        source = called_number_source(assistant_number)
        if conversation is None or conversation.acquisition_source or source is None:
            return

        conversation.acquisition_source = source
        self._conversation_repo.save(conversation)
