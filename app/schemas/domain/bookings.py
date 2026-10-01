from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.constants.bookings import BookingStatus, LeadStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    LeadBudgetText,
    LeadDetails,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId, CustomerName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.questionnaires.strings import ResourceName


class BookingDocument(BaseDocument):
    """Booking of a resource; times are UTC, rendering uses the business zone."""

    id: BookingId = Field(default_factory=BookingId)
    business_id: BusinessId
    conversation_id: ConversationId | None = None
    resource_name: ResourceName
    starts_at: BookingStartsAtUnixSeconds
    ends_at: BookingEndsAtUnixSeconds
    party_size: PartySize
    customer_name: CustomerName
    customer_phone_number: E164PhoneNumber | None = None
    channel: ChannelKind
    channel_user_id: ChannelUserId | None = None
    language: LanguageTag
    status: BookingStatus = BookingStatus.CONFIRMED
    note: BookingNote | None = None
    is_sandbox: IsSandboxConversation = False


class LeadDocument(BaseDocument):
    """Request that needs a manager: banquet, group stay, order, viewing."""

    id: LeadId = Field(default_factory=LeadId)
    business_id: BusinessId
    conversation_id: ConversationId | None = None
    customer_name: CustomerName
    customer_phone_number: E164PhoneNumber | None = None
    details: LeadDetails
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None
    channel: ChannelKind
    language: LanguageTag
    status: LeadStatus = LeadStatus.NEW
    is_sandbox: IsSandboxConversation = False
