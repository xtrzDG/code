"""
The erasure of one customer's personal data (right to erasure), shared by
the owner's request (`DeleteContactDataUseCase`) and its re-application
after a restore from backup (`ReapplyContactErasuresUseCase`).
"""

from typed_time_provider import Microseconds

from app.contracts.calendar_erasure import CalendarGuestErasureFacilitatorContract
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
from app.contracts.repositories.consent_repositories import ConsentRecordRepoContract
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
from app.contracts.repositories.integration_repositories import (
    WebhookDeliveryRepoContract,
)
from app.contracts.repositories.media_repositories import (
    MessageMediaRepoContract,
    WidgetUploadRepoContract,
)
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.schemas.constants.consent_records import ConsentEventSource
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.privacy import ProcessorErasureReason
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.compliance import ContactErasureResult, ContactRecords
from app.schemas.dto.customers.consent_records import ConsentOrigin
from app.schemas.dto.privacy.suppression import SuppressedIdentity
from app.schemas.dto.processor_erasure import ProcessorErasureScope
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    DeletedRecordingCount,
    ErasedRecordCount,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.privacy.constrained_integers import ProcessorErasureJobCount
from app.use_cases.compliance.contact_file_erasure import ContactFileEraser
from app.use_cases.compliance.contact_trace_erasure import (
    ContactTraceEraser,
    TraceErasure,
)
from app.use_cases.compliance.record_anonymization import (
    BusinessRecordAnonymizer,
    erased_call,
)
from app.use_cases.shared.consent_ledger import record_consent_change
from app.utilities.privacy.erased_conversations import ERASED_CHANNEL_USER_ID_PREFIX
from app.utilities.privacy.suppressed_identities import contact_identities


class ContactDataEraser:
    """
    Erases what the platform keeps of one customer (`erase`).

    Recordings, voice notes and photos (the website chat's original uploads
    too) go from storage first, so a storage failure leaves the database
    untouched and the erasure can be retried (`contact_file_erasure`). Then
    the messages, model transcripts, the team's internal notes of their
    conversations and call transcripts are deleted, and the contact keeps
    only its id and the erasure time (no name, phones, language, channel
    identities or marketing consent): the cabinet shows it as erased and a
    new message from the same person starts a new contact. Business
    records stay but lose the personal parts: conversations lose the
    channel identity, bookings their notes, leads their details and budget,
    handoffs their summary. Missed calls, queued messages, webhook events
    and requests for feedback lose what identifies the person, the
    outbound webhooks' deliveries about them go (`contact_trace_erasure`).
    A customer who said STOP stays on the suppression list (only digests,
    kept on purpose), so the erasure never makes them reachable again, and
    every erased customer leaves the digests of their numbers and accounts
    as erasure entries (`remember_erasure`), so no marketing on a consent
    given before the erasure reaches them (a restored backup's); a consent
    still given is taken back in the consent ledger, which keeps the
    customer's history by contact id only as proof. The
    copies the sub-processors keep (the traces of the conversations' model
    calls at Langfuse, the calls at ElevenLabs) are deleted by queued jobs
    with retries (`processor_erasure`), so a processor's outage never fails
    the erasure. The events the bookings have in the business's Google
    Calendar go last (`calendar_erasure`): rewritten without the guest
    while the booking still takes its time, deleted otherwise. Erasing
    what is gone already is no error, so it runs again after a restore.
    """

    def __init__(
        self,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        llm_turn_repo: LlmTurnRepoContract,
        call_repo: CallRepoContract,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        handoff_repo: HandoffRepoContract,
        recording_storage: RecordingStorageAdapterContract,
        note_repo: ConversationNoteRepoContract,
        media_storage: MediaStorageAdapterContract,
        message_media_repo: MessageMediaRepoContract,
        suppression_list: SuppressionListContract,
        missed_call_repo: MissedCallRepoContract,
        outbound_message_repo: OutboundMessageRepoContract,
        inbound_event_repo: InboundEventRepoContract,
        feedback_request_repo: FeedbackRequestRepoContract,
        processor_erasure: ProcessorErasureFacilitatorContract,
        widget_upload_repo: WidgetUploadRepoContract,
        waitlist_entry_repo: WaitlistEntryRepoContract | None = None,
        webhook_delivery_repo: WebhookDeliveryRepoContract | None = None,
        calendar_erasure: CalendarGuestErasureFacilitatorContract | None = None,
        consent_record_repo: ConsentRecordRepoContract | None = None,
    ) -> None:
        self._consent_record_repo: ConsentRecordRepoContract | None = (
            consent_record_repo
        )
        self._calendar_erasure: CalendarGuestErasureFacilitatorContract | None = (
            calendar_erasure
        )
        self._processor_erasure: ProcessorErasureFacilitatorContract = processor_erasure
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._llm_turn_repo: LlmTurnRepoContract = llm_turn_repo
        self._call_repo: CallRepoContract = call_repo
        self._note_repo: ConversationNoteRepoContract = note_repo
        self._suppression_list: SuppressionListContract = suppression_list
        self._files: ContactFileEraser = ContactFileEraser(
            recording_storage, media_storage, message_media_repo, widget_upload_repo
        )
        self._records: BusinessRecordAnonymizer = BusinessRecordAnonymizer(
            booking_repo, lead_repo, handoff_repo
        )
        self._traces: ContactTraceEraser = ContactTraceEraser(
            missed_call_repo, outbound_message_repo, inbound_event_repo,
            feedback_request_repo, waitlist_entry_repo, webhook_delivery_repo,
        )  # fmt: skip

    def erase(self, records: ContactRecords, now: Microseconds) -> ContactErasureResult:
        """Erase the customer these records are of; what was erased."""

        contact: ContactDocument = records.contact
        business_id: BusinessId = contact.business_id
        identities: list[SuppressedIdentity] = contact_identities(contact)
        if contact.opted_out_channels:
            # A STOP from before the suppression list: it outlives the erasure.
            self._suppression_list.suppress(business_id, identities, now)
        # Every erased customer leaves digests only: no marketing on a
        # consent from before the erasure ever reaches them again.
        self._suppression_list.remember_erasure(business_id, identities, now)
        # The ledger keeps the proof; the erasure takes the consent back.
        record_consent_change(
            self._consent_record_repo,
            contact,
            contact.marketing_consent,
            None,
            ConsentOrigin(source=ConsentEventSource.ERASURE),
            now,
        )

        deleted_recordings: DeletedRecordingCount = self._files.erase(records)
        traces: TraceErasure = self._traces.erase(records, now)
        self._erase_calls(records, now)
        deleted_llm_turns: int = self._erase_conversations(business_id, records, now)
        self._records.anonymize(records, now)
        queued: ProcessorErasureJobCount = self._processor_erasure.request_erasure(
            ProcessorErasureScope(
                business_id=business_id,
                reason=ProcessorErasureReason.CONTACT_ERASURE,
                conversation_ids=[item.id for item in records.conversations],
                provider_call_ids=[call.provider_call_id for call in records.calls],
            )
        )
        self._contact_repo.save(
            ContactDocument(
                id=contact.id,
                business_id=business_id,
                erased_at=now,
                # The erasure is the customer's latest event in the list.
                last_seen_at=now,
                created_at=contact.created_at,
                updated_at=now,
            )
        )
        if self._calendar_erasure is not None:
            # Last: the events are rewritten from what the erasure left.
            self._calendar_erasure.forget_guest(records.bookings)
        return ContactErasureResult(
            business_id=business_id,
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
        business_id: BusinessId,
        records: ContactRecords,
        now: Microseconds,
    ) -> int:
        deleted_llm_turns: int = 0
        for conversation in records.conversations:
            self._message_repo.delete_by_conversation(business_id, conversation.id)
            deleted_llm_turns += len(
                self._llm_turn_repo.list_by_conversation(conversation.id)
            )
            self._llm_turn_repo.delete_by_conversation(conversation.id)
            # The team's notes on the conversation are about this person.
            self._note_repo.delete_by_conversation(business_id, conversation.id)
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
