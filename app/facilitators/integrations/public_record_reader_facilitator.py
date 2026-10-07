"""A business's records in their public shape (webhooks and the public API)."""

from collections.abc import Sequence

from app.contracts.integrations import PublicRecordReaderContract
from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.public_api.activity import (
    PublicCall,
    PublicConversation,
    PublicConversationDetail,
    PublicHandoff,
)
from app.schemas.dto.public_api.records import PublicBooking, PublicContact, PublicLead
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.utilities.integrations.public_views import (
    public_booking,
    public_call,
    public_contact,
    public_conversation,
    public_handoff,
    public_lead,
    public_message,
)

# A conversation's detail shows its latest messages, oldest first.
DETAIL_MESSAGE_LIMIT: KeysetReadLimit = KeysetReadLimit(100)


class PublicRecordReaderFacilitator(PublicRecordReaderContract):
    """
    Reads one record of the business with what its public shape names:
    the customer, the resource and service of a booking, the conversation
    the customer came through (its acquisition source). Every read names
    the business, so a record of another business reads as missing.
    """

    def __init__(
        self,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        handoff_repo: HandoffRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        call_repo: CallRepoContract,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._call_repo: CallRepoContract = call_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def booking(
        self, business: BusinessDocument, booking_id: BookingId
    ) -> PublicBooking | None:
        booking = self._booking_repo.get(business.id, booking_id)
        if booking is None or booking.is_sandbox:
            return None

        return self.bookings(business, [booking])[0]

    def lead(self, business: BusinessDocument, lead_id: LeadId) -> PublicLead | None:
        lead = self._lead_repo.get(business.id, lead_id)
        if lead is None or lead.is_sandbox:
            return None

        return self.leads(business, [lead])[0]

    def contact(
        self, business: BusinessDocument, contact_id: ContactId
    ) -> PublicContact | None:
        contact = self._contact_repo.get(business.id, contact_id)
        return None if contact is None else public_contact(contact)

    def conversation(
        self, business: BusinessDocument, conversation_id: ConversationId
    ) -> PublicConversation | None:
        conversation = self._conversation_of(business, conversation_id)
        if conversation is None or conversation.is_sandbox:
            return None

        return self.conversations(business, [conversation])[0]

    def conversation_detail(
        self, business: BusinessDocument, conversation_id: ConversationId
    ) -> PublicConversationDetail | None:
        summary = self.conversation(business, conversation_id)
        if summary is None:
            return None

        newest_first = self._message_repo.page_transcript(
            business.id, conversation_id, KeysetSlice(limit=DETAIL_MESSAGE_LIMIT)
        )
        return PublicConversationDetail(
            **summary.model_dump(),
            messages=[public_message(message) for message in reversed(newest_first)],
        )

    def handoff(
        self, business: BusinessDocument, handoff_id: HandoffId
    ) -> PublicHandoff | None:
        handoff = self._handoff_repo.get(business.id, handoff_id)
        if handoff is None:
            return None

        return public_handoff(
            handoff, self._contact_repo.get(business.id, handoff.contact_id)
        )

    def call(self, business: BusinessDocument, call_id: CallId) -> PublicCall | None:
        call = self._call_repo.get(business.id, call_id)
        if call is None:
            return None

        conversation = self._conversation_of(business, call.conversation_id)
        return public_call(
            call,
            conversation,
            None
            if conversation is None
            else self._contact_repo.get(business.id, conversation.contact_id),
        )

    def bookings(
        self, business: BusinessDocument, bookings: Sequence[BookingDocument]
    ) -> list[PublicBooking]:
        contacts = self._contact_repo.get_many(
            business.id, [booking.contact_id for booking in bookings]
        )
        return [
            public_booking(
                business,
                booking,
                contacts.get(booking.contact_id),
                self._resource_repo.get(business.id, booking.resource_id),
                None
                if booking.service_item_id is None
                else self._knowledge_item_repo.get(
                    business.id, booking.service_item_id
                ),
                self._conversation_of(business, booking.conversation_id),
            )
            for booking in bookings
        ]

    def leads(
        self, business: BusinessDocument, leads: Sequence[LeadDocument]
    ) -> list[PublicLead]:
        contacts = self._contact_repo.get_many(
            business.id, [lead.contact_id for lead in leads]
        )
        return [
            public_lead(
                lead,
                contacts.get(lead.contact_id),
                self._conversation_of(business, lead.conversation_id),
            )
            for lead in leads
        ]

    def conversations(
        self, business: BusinessDocument, conversations: Sequence[ConversationDocument]
    ) -> list[PublicConversation]:
        contacts = self._contact_repo.get_many(
            business.id, [conversation.contact_id for conversation in conversations]
        )
        return [
            public_conversation(conversation, contacts.get(conversation.contact_id))
            for conversation in conversations
        ]

    def _conversation_of(
        self, business: BusinessDocument, conversation_id: ConversationId | None
    ) -> ConversationDocument | None:
        if conversation_id is None:
            return None

        return self._conversation_repo.get(business.id, conversation_id)
