from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId, ResourceId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    LeadBudgetText,
    LeadDetails,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId


class BookingDocument(BaseDocument):
    """Booking of a resource (concept table `bookings`); times are UTC."""

    id: BookingId = Field(default_factory=BookingId)
    business_id: BusinessId
    resource_id: ResourceId
    contact_id: ContactId
    conversation_id: ConversationId | None = None
    starts_at: BookingStartsAtUnixSeconds
    ends_at: BookingEndsAtUnixSeconds
    party_size: PartySize
    status: BookingStatus = BookingStatus.CONFIRMED
    source_channel: ChannelKind
    notes: BookingNote | None = None
    is_sandbox: IsSandboxConversation = False
    # When the customer's reminder went out (UTC microseconds); None = not yet.
    reminder_sent_at: Microseconds | None = None


class LeadDocument(BaseDocument):
    """Request for a manager (concept table `leads`)."""

    id: LeadId = Field(default_factory=LeadId)
    business_id: BusinessId
    contact_id: ContactId
    conversation_id: ConversationId | None = None
    lead_type: LeadType
    details: LeadDetails
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None
    source_channel: ChannelKind
    status: LeadStatus = LeadStatus.NEW
    is_sandbox: IsSandboxConversation = False
