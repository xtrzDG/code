from typed_time_provider import Microseconds, WallClock

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    LlmTurnRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.call_recordings import RecordingLocation
from app.schemas.dto.compliance import (
    ContactDataCommand,
    ContactErasureResult,
    ContactRecords,
    ContactRecordsQuery,
)
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.compliance.constrained_integers import (
    DeletedRecordingCount,
    ErasedRecordCount,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.handoffs.strings import HandoffSummary

ERASED_TEXT: str = "[erased at the visitor's request]"
ERASED_CHANNEL_USER_ID_PREFIX: str = "erased-"


class DeleteContactDataUseCase(
    UseCaseContract[ContactDataCommand, ContactErasureResult]
):
    """
    Owner erases one visitor's personal data (right to erasure).

    Recordings are deleted from storage first, so a storage failure leaves
    the database untouched and the erasure can be retried. Then the messages,
    model transcripts and the team's internal notes of their conversations
    and call transcripts are deleted, and the contact keeps only its id and
    the erasure time (no name, phones, language or channel identities), so
    the cabinet shows it as erased and a new message from the same person
    starts a new contact.
    Business records stay but lose the personal parts: conversations lose
    the channel identity, bookings their notes, leads their details and
    budget, handoffs their summary. The erasure is audited with the contact
    id only.
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
    ) -> None:
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
        self._recording_storage: RecordingStorageAdapterContract = recording_storage
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ContactDataCommand) -> ContactErasureResult:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        records: ContactRecords = self._collect_contact_records.run(
            ContactRecordsQuery(
                business_id=business.id,
                contact_id=input_data.contact_id,
            )
        )
        contact: ContactDocument = records.contact
        now: Microseconds = self._wall_clock.now_unix()
        deleted_recordings: int = self._delete_recordings(records)
        self._erase_calls(records, now)
        deleted_llm_turns: int = self._erase_conversations(business, records, now)
        self._anonymize_business_records(records, now)
        self._contact_repo.save(
            ContactDocument(
                id=contact.id,
                business_id=business.id,
                erased_at=now,
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
            deleted_recordings=DeletedRecordingCount(deleted_recordings),
            anonymized_conversations=ErasedRecordCount(len(records.conversations)),
            anonymized_bookings=ErasedRecordCount(len(records.bookings)),
            anonymized_leads=ErasedRecordCount(len(records.leads)),
            anonymized_handoffs=ErasedRecordCount(len(records.handoffs)),
            deleted_notes=ErasedRecordCount(len(records.notes)),
        )

    def _delete_recordings(self, records: ContactRecords) -> int:
        deleted_recordings: int = 0
        for call in records.calls:
            if call.recording_path is not None:
                self._recording_storage.delete(
                    RecordingLocation(
                        business_id=call.business_id, path=call.recording_path
                    )
                )
                deleted_recordings += 1

        return deleted_recordings

    def _erase_calls(self, records: ContactRecords, now: Microseconds) -> None:
        for call in records.calls:
            call.recording_path = None
            call.transcript = None
            call.from_phone_number = None
            if call.to_phone_number == records.contact.phone_number:
                call.to_phone_number = None

            call.updated_at = now
            self._call_repo.save(call)

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
            conversation.updated_at = now
            self._conversation_repo.save(conversation)

        return deleted_llm_turns

    def _anonymize_business_records(
        self,
        records: ContactRecords,
        now: Microseconds,
    ) -> None:
        for booking in records.bookings:
            booking.notes = None
            booking.updated_at = now
            self._booking_repo.save(booking)

        for lead in records.leads:
            lead.details = LeadDetails(ERASED_TEXT)
            lead.budget = None
            lead.updated_at = now
            self._lead_repo.save(lead)

        for handoff in records.handoffs:
            handoff.summary = HandoffSummary(ERASED_TEXT)
            handoff.updated_at = now
            self._handoff_repo.save(handoff)
