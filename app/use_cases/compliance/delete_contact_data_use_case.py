from typed_time_provider import Microseconds, WallClock

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.privacy import SuppressionListContract
from app.contracts.processor_erasure import ProcessorErasureFacilitatorContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.call_follow_up_repositories import (
    MissedCallRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    LlmTurnRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    InboundEventRepoContract,
    OutboundMessageRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
)
from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.constants.privacy import ProcessorErasureReason
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.compliance import (
    ContactDataCommand,
    ContactErasureResult,
    ContactRecords,
    ContactRecordsQuery,
)
from app.schemas.dto.processor_erasure import ProcessorErasureScope
from app.schemas.typings.compliance.constrained_integers import (
    DeletedRecordingCount,
    ErasedRecordCount,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.privacy.constrained_integers import ProcessorErasureJobCount
from app.use_cases.compliance.contact_file_erasure import ContactFileEraser
from app.use_cases.compliance.contact_trace_erasure import (
    ContactTraceEraser,
    TraceErasure,
)
from app.use_cases.compliance.record_anonymization import (
    ERASED_TEXT,
    anonymized_booking,
    anonymized_handoff,
    anonymized_lead,
    erased_call,
)
from app.utilities.privacy.erased_conversations import ERASED_CHANNEL_USER_ID_PREFIX
from app.utilities.privacy.suppressed_identities import contact_identities


class DeleteContactDataUseCase(
    UseCaseContract[ContactDataCommand, ContactErasureResult]
):
    """
    Owner erases one visitor's personal data (right to erasure).

    Recordings, voice notes and photos are deleted from storage first, so a
    storage failure leaves the database untouched and the erasure can be
    retried (`contact_file_erasure`). Then the messages,
    model transcripts and the team's internal notes of their conversations
    and call transcripts are deleted, and the contact keeps only its id and
    the erasure time (no name, phones, language or channel identities), so
    the cabinet shows it as erased and a new message from the same person
    starts a new contact.
    Business records stay but lose the personal parts: conversations lose
    the channel identity, bookings their notes, leads their details and
    budget, handoffs their summary. Missed calls, queued messages, webhook
    events and requests for feedback lose what identifies the person
    (`contact_trace_erasure`). A customer who said STOP stays on the
    suppression list (only digests, kept on purpose), so the erasure never
    makes them reachable again. The copies the sub-processors keep (the
    traces of the conversations' model calls at Langfuse, the calls at
    ElevenLabs) are deleted by queued jobs with retries
    (`processor_erasure`), so a processor's outage never fails the
    erasure. The erasure is audited with the contact id only.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        collect_contact_records: UseCaseContract[ContactRecordsQuery, ContactRecords],
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        llm_turn_repo: LlmTurnRepoContract,
        call_repo: CallRepoContract,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        handoff_repo: HandoffRepoContract,
        recording_storage: RecordingStorageAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        note_repo: ConversationNoteRepoContract,
        media_storage: MediaStorageAdapterContract,
        message_media_repo: MessageMediaRepoContract,
        step_up: StepUpGuardContract,
        suppression_list: SuppressionListContract,
        missed_call_repo: MissedCallRepoContract,
        outbound_message_repo: OutboundMessageRepoContract,
        inbound_event_repo: InboundEventRepoContract,
        feedback_request_repo: FeedbackRequestRepoContract,
        processor_erasure: ProcessorErasureFacilitatorContract,
        waitlist_entry_repo: WaitlistEntryRepoContract | None = None,
    ) -> None:
        self._processor_erasure: ProcessorErasureFacilitatorContract = processor_erasure
        self._step_up: StepUpGuardContract = step_up
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._collect_contact_records: UseCaseContract[
            ContactRecordsQuery,
            ContactRecords,
        ] = collect_contact_records
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._llm_turn_repo: LlmTurnRepoContract = llm_turn_repo
        self._call_repo: CallRepoContract = call_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._note_repo: ConversationNoteRepoContract = note_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._suppression_list: SuppressionListContract = suppression_list
        self._files: ContactFileEraser = ContactFileEraser(
            recording_storage, media_storage, message_media_repo
        )
        self._traces: ContactTraceEraser = ContactTraceEraser(
            missed_call_repo,
            outbound_message_repo,
            inbound_event_repo,
            feedback_request_repo,
            waitlist_entry_repo,
        )

    def run(self, input_data: ContactDataCommand) -> ContactErasureResult:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        self._step_up.require_recent_authentication()
        records: ContactRecords = self._collect_contact_records.run(
            ContactRecordsQuery(
                business_id=business.id,
                contact_id=input_data.contact_id,
            )
        )
        contact: ContactDocument = records.contact
        now: Microseconds = self._wall_clock.now_unix()
        if contact.opted_out_channels:
            # A STOP from before the suppression list: it outlives the erasure.
            self._suppression_list.suppress(
                business.id, contact_identities(contact), now
            )

        deleted_recordings: DeletedRecordingCount = self._files.erase(records)
        traces: TraceErasure = self._traces.erase(records, now)
        self._erase_calls(records, now)
        deleted_llm_turns: int = self._erase_conversations(business, records, now)
        self._anonymize_business_records(records, now)
        queued: ProcessorErasureJobCount = self._processor_erasure.request_erasure(
            ProcessorErasureScope(
                business_id=business.id,
                reason=ProcessorErasureReason.CONTACT_ERASURE,
                conversation_ids=[item.id for item in records.conversations],
                provider_call_ids=[call.provider_call_id for call in records.calls],
            )
        )
        self._contact_repo.save(
            ContactDocument(
                id=contact.id,
                business_id=business.id,
                erased_at=now,
                # The erasure is the customer's latest event in the list.
                last_seen_at=now,
                created_at=contact.created_at,
                updated_at=now,
            )
        )
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.DELETE,
                entity=AuditEntityName("contact"),
                entity_id=AuditEntityReference(str(contact.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return ContactErasureResult(
            business_id=business.id,
            contact_id=contact.id,
            deleted_messages=ErasedRecordCount(len(records.messages)),
            deleted_llm_turns=ErasedRecordCount(deleted_llm_turns),
            erased_calls=ErasedRecordCount(len(records.calls)),
            deleted_recordings=deleted_recordings,
            anonymized_conversations=ErasedRecordCount(len(records.conversations)),
            anonymized_bookings=ErasedRecordCount(len(records.bookings)),
            anonymized_leads=ErasedRecordCount(len(records.leads)),
            anonymized_handoffs=ErasedRecordCount(len(records.handoffs)),
            deleted_notes=ErasedRecordCount(len(records.notes)),
            erased_missed_calls=traces.missed_calls,
            redacted_outbound_messages=traces.outbound_messages,
            redacted_inbound_events=traces.inbound_events,
            anonymized_feedback_requests=traces.feedback_requests,
            anonymized_waitlist_entries=traces.waitlist_entries,
            queued_processor_erasures=queued,
        )

    def _erase_calls(self, records: ContactRecords, now: Microseconds) -> None:
        for call in records.calls:
            erased = erased_call(call, now, records.contact.phone_number)
            if erased is not None:
                self._call_repo.save(erased)

    def _erase_conversations(
        self,
        business: BusinessDocument,
        records: ContactRecords,
        now: Microseconds,
    ) -> int:
        deleted_llm_turns: int = 0
        for conversation in records.conversations:
            self._message_repo.delete_by_conversation(business.id, conversation.id)
            deleted_llm_turns += len(
                self._llm_turn_repo.list_by_conversation(conversation.id)
            )
            self._llm_turn_repo.delete_by_conversation(conversation.id)
            # The team's notes on the conversation are about this person.
            self._note_repo.delete_by_conversation(business.id, conversation.id)
            conversation.channel_user_id = ChannelUserId(
                f"{ERASED_CHANNEL_USER_ID_PREFIX}{conversation.id}"
            )
            conversation.status = ConversationStatus.CLOSED
            # What the customer memory remembered of it is about this person.
            conversation.summary = None
            conversation.summarized_at = None
            conversation.updated_at = now
            self._conversation_repo.save(conversation)

        return deleted_llm_turns

    def _anonymize_business_records(
        self,
        records: ContactRecords,
        now: Microseconds,
    ) -> None:
        for booking in records.bookings:
            if (anonymized := anonymized_booking(booking, now)) is not None:
                self._booking_repo.save(anonymized)

        for lead in records.leads:
            if (lead_left := anonymized_lead(lead, ERASED_TEXT, now)) is not None:
                self._lead_repo.save(lead_left)

        for handoff in records.handoffs:
            # The cabinet shows the code in the reader's language.
            handoff_left = anonymized_handoff(
                handoff, ERASED_TEXT, HandoffSummaryCode.DATA_ERASED, now
            )
            if handoff_left is not None:
                self._handoff_repo.save(handoff_left)
