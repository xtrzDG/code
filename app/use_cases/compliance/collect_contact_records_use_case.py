from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.call_follow_up_repositories import (
    MissedCallRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
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
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.dto.compliance import ContactRecords, ContactRecordsQuery
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.use_cases.compliance.contact_traces import ContactTraceReader, ContactTraces


class CollectContactRecordsUseCase(
    UseCaseContract[ContactRecordsQuery, ContactRecords]
):
    """
    Gather every record about one visitor inside one business.

    The team's internal notes on the visitor's conversations are records
    about them too, and so are their traces outside the conversations:
    missed calls, queued messages, webhook events and requests for
    feedback (`contact_traces`). Every read goes through the business id,
    so a contact id of another business is reported as missing, and so is
    an erased contact (nothing personal is left to export or erase).
    Callers check access first.
    """

    def __init__(
        self,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        call_repo: CallRepoContract,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        handoff_repo: HandoffRepoContract,
        note_repo: ConversationNoteRepoContract,
        channel_repo: ChannelRepoContract,
        missed_call_repo: MissedCallRepoContract,
        outbound_message_repo: OutboundMessageRepoContract,
        inbound_event_repo: InboundEventRepoContract,
        feedback_request_repo: FeedbackRequestRepoContract,
    ) -> None:
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._call_repo: CallRepoContract = call_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._note_repo: ConversationNoteRepoContract = note_repo
        self._traces: ContactTraceReader = ContactTraceReader(
            channel_repo=channel_repo,
            missed_call_repo=missed_call_repo,
            outbound_message_repo=outbound_message_repo,
            inbound_event_repo=inbound_event_repo,
            feedback_request_repo=feedback_request_repo,
        )

    def run(self, input_data: ContactRecordsQuery) -> ContactRecords:
        contact: ContactDocument | None = self._contact_repo.get(
            input_data.business_id,
            input_data.contact_id,
        )
        if contact is None or contact.erased_at is not None:
            raise NotFoundError(f"Contact {input_data.contact_id} was not found.")

        conversations: list[ConversationDocument] = sorted(
            (
                conversation
                for conversation in self._conversation_repo.list_by_business(
                    contact.business_id
                )
                if conversation.contact_id == contact.id
            ),
            key=lambda conversation: conversation.created_at,
        )
        conversation_ids: set[ConversationId] = {
            conversation.id for conversation in conversations
        }
        messages: list[MessageDocument] = [
            message
            for conversation in conversations
            for message in self._message_repo.list_by_conversation(
                contact.business_id,
                conversation.id,
            )
        ]
        calls: list[CallDocument] = sorted(
            (
                call
                for call in self._call_repo.list_by_business(contact.business_id)
                if call.conversation_id in conversation_ids
                or (
                    contact.phone_number is not None
                    and call.from_phone_number == contact.phone_number
                )
            ),
            key=lambda call: call.started_at,
        )
        traces: ContactTraces = self._traces.read(contact, conversations)
        return ContactRecords(
            contact=contact,
            conversations=conversations,
            messages=messages,
            calls=calls,
            bookings=[
                booking
                for booking in self._booking_repo.list_by_business(contact.business_id)
                if booking.contact_id == contact.id
            ],
            leads=[
                lead
                for lead in self._lead_repo.list_by_business(contact.business_id)
                if lead.contact_id == contact.id
            ],
            handoffs=[
                handoff
                for handoff in self._handoff_repo.list_by_business(contact.business_id)
                if handoff.contact_id == contact.id
            ],
            notes=[
                note
                for conversation in conversations
                for note in self._note_repo.list_by_conversation(
                    contact.business_id, conversation.id
                )
            ],
            missed_calls=traces.missed_calls,
            outbound_messages=traces.outbound_messages,
            inbound_events=traces.inbound_events,
            feedback_requests=traces.feedback_requests,
        )
