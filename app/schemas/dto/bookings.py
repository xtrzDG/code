from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.bookings import BookingStatus, LeadStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.bookings.booleans import IsOpenOnDate
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
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
    TimezoneName,
)
from app.schemas.typings.questionnaires.strings import ResourceName


class AvailabilityQuery(ImmutableDTO):
    """Free slots on a local date, optionally near a time and for a group."""

    business_id: BusinessId
    date: LocalDate
    time: LocalTimeOfDay | None = None
    party_size: PartySize | None = None
    resource_name: ResourceName | None = None


class AvailableSlot(ImmutableDTO):
    """One free slot in the business time zone."""

    resource_name: ResourceName
    date: LocalDate
    time: LocalTimeOfDay
    duration_minutes: BookingDurationMinutes


class AvailabilityResult(ImmutableDTO):
    """Free slots for a query; empty when closed or fully booked."""

    timezone: TimezoneName
    is_open_on_date: IsOpenOnDate
    slots: list[AvailableSlot] = Field(default_factory=list[AvailableSlot])


class CreateBookingCommand(ImmutableDTO):
    """Book a resource at a local date and time of the business."""

    business_id: BusinessId
    conversation_id: ConversationId | None = None
    resource_name: ResourceName | None = None
    date: LocalDate
    time: LocalTimeOfDay
    party_size: PartySize
    customer_name: CustomerName
    customer_phone_number: E164PhoneNumber | None = None
    duration_minutes: BookingDurationMinutes | None = None
    note: BookingNote | None = None
    channel: ChannelKind
    channel_user_id: ChannelUserId | None = None
    language: LanguageTag
    is_sandbox: IsSandboxConversation = False


class CancelBookingCommand(ImmutableDTO):
    """Cancel a booking found by id, or by the customer's phone and date."""

    business_id: BusinessId
    booking_id: BookingId | None = None
    conversation_id: ConversationId | None = None
    customer_phone_number: E164PhoneNumber | None = None
    date: LocalDate | None = None


class BookingView(ImmutableDTO):
    """Booking rendered in the business time zone."""

    id: BookingId
    business_id: BusinessId
    resource_name: ResourceName
    date: LocalDate
    time: LocalTimeOfDay
    duration_minutes: BookingDurationMinutes
    timezone: TimezoneName
    party_size: PartySize
    customer_name: CustomerName
    customer_phone_number: E164PhoneNumber | None = None
    channel: ChannelKind
    status: BookingStatus
    note: BookingNote | None = None
    is_sandbox: IsSandboxConversation = False


class CreateLeadCommand(ImmutableDTO):
    """Create a request for a manager."""

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
    is_sandbox: IsSandboxConversation = False


class LeadView(ImmutableDTO):
    """Lead as shown to the owner."""

    id: LeadId
    business_id: BusinessId
    customer_name: CustomerName
    customer_phone_number: E164PhoneNumber | None = None
    details: LeadDetails
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None
    channel: ChannelKind
    language: LanguageTag
    status: LeadStatus
    is_sandbox: IsSandboxConversation = False
