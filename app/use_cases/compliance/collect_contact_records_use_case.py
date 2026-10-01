from app.contracts.repositories import (
    BookingRepoContract,
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
    MessageRepoContract,
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


class CollectContactRecordsUseCase(
    UseCaseContract[ContactRecordsQuery, ContactRecords]
):
    """
    Gather every record about one visitor inside one business.

    Every read goes through the business id, so a contact id of another
    business is reported as missing. Callers check access first.
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
    ) -> None:
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._call_repo: CallRepoContract = call_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo

    def run(self, input_data: ContactRecordsQuery) -> ContactRecords:
        contact: ContactDocument | None = self._contact_repo.get(
            input_data.business_id,
            input_data.contact_id,
        )
        if contact is None:
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
        )
