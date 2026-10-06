from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import (
    BookingStatus,
    BookingUnit,
    LeadStatus,
    LeadType,
    ResourceKind,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.bookable_offers import BookableOfferView, StayQuote
from app.schemas.typings.bookings.booleans import (
    IsFullDayAvailability,
    IsOpenOnDate,
    ListsEveryFreeTime,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    BookingStartsAtUnixSeconds,
    BookingValueMinor,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId, ResourceId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    LeadBudgetText,
    LeadDetails,
    ResourceName,
    ResourceReference,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle, ServiceReference
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.waitlist.booleans import IsWaitlistEnabled


class AvailabilityQuery(ImmutableDTO):
    """
    Free slots (or free nights) on a local date of the business.

    Time-slot resources use `time` and `duration_minutes`; night resources
    use `nights`. Times are in the business time zone, with schedule
    exceptions (holidays) applied.

    A sandbox query from a test conversation (`conversation_id`) sees that
    conversation's own test bookings, not those of other tests.

    `full_day` is the staff view: every free slot of the date for every
    matching resource (no nearest-time or count limit), by the cabinet's
    rules (no minimum notice, no online party-size limit).

    A service (`service_reference` from the model: an id or a name in any
    script; `service_item_id` from the cabinet) sets the length and buffer
    and limits the slots to its performers; `resource_reference` names a
    resource the same way ("Nino", "ნინო").
    """

    business_id: BusinessId
    date: LocalDate
    resource_kind: ResourceKind | None = None
    resource_id: ResourceId | None = None
    resource_reference: ResourceReference | None = None
    service_reference: ServiceReference | None = None
    service_item_id: KnowledgeItemId | None = None
    time: LocalTimeOfDay | None = None
    party_size: PartySize | None = None
    duration_minutes: BookingDurationMinutes | None = None
    nights: NightCount | None = None
    is_sandbox: IsSandboxConversation = False
    conversation_id: ConversationId | None = None
    full_day: IsFullDayAvailability = False
    # A guest moving their booking: every free time of the date by the
    # customer rules, and the booking itself does not block its own time.
    lists_every_time: ListsEveryFreeTime = False
    excluded_booking_id: BookingId | None = None
    # The customer asking: a place held for them on the waitlist is free.
    contact_id: ContactId | None = None


class AvailableSlot(ImmutableDTO):
    """
    One free slot or stay in the business time zone; a stay of a priced
    room type carries its quote (each night at its season's rate).
    """

    resource_id: ResourceId
    resource_name: ResourceName
    booking_unit: BookingUnit
    date: LocalDate
    time: LocalTimeOfDay | None = None
    duration_minutes: BookingDurationMinutes | None = None
    nights: NightCount | None = None
    stay_quote: StayQuote | None = None


class AvailabilityResult(ImmutableDTO):
    """
    Free slots for a query; empty when closed or fully booked. `service` is
    the service the query named; without one, `services` lists the
    business's bookable offers with their ids, so the model can name one.
    """

    timezone: TimezoneName
    is_open_on_date: IsOpenOnDate
    slots: list[AvailableSlot] = Field(default_factory=list[AvailableSlot])
    service: BookableOfferView | None = None
    services: list[BookableOfferView] = Field(default_factory=list[BookableOfferView])
    # Nothing free, and the business keeps a waitlist (join_waitlist).
    is_waitlist_open: IsWaitlistEnabled = False


class CreateBookingCommand(ImmutableDTO):
    """
    Book a resource at a local date (and time) of the business.

    The contact is resolved by the server; name and phone from the
    conversation update the contact. A service and a resource may be named
    by id or by a name in any script (as in `AvailabilityQuery`).
    """

    business_id: BusinessId
    contact_id: ContactId
    conversation_id: ConversationId | None = None
    contact_name: ContactName
    contact_phone_number: E164PhoneNumber | None = None
    resource_kind: ResourceKind | None = None
    resource_id: ResourceId | None = None
    resource_reference: ResourceReference | None = None
    service_reference: ServiceReference | None = None
    date: LocalDate
    time: LocalTimeOfDay | None = None
    duration_minutes: BookingDurationMinutes | None = None
    nights: NightCount | None = None
    party_size: PartySize
    notes: BookingNote | None = None
    source_channel: ChannelKind
    language: LanguageTag
    is_sandbox: IsSandboxConversation = False


class RescheduleBookingCommand(ImmutableDTO):
    """
    Move a booking found by id, or by contact phone and old date.

    A customer request (contact or phone given) reaches only bookings of
    the same sandbox mode: owner tests never touch real bookings and real
    customers never touch test bookings. `is_sandbox` None (cabinet) does
    not filter. `expected_starts_at` (a guest's manage link) moves the
    booking only while it still starts then (checked under the lock).
    """

    business_id: BusinessId
    contact_id: ContactId | None = None
    booking_id: BookingId | None = None
    contact_phone_number: E164PhoneNumber | None = None
    old_date: LocalDate | None = None
    new_date: LocalDate
    new_time: LocalTimeOfDay | None = None
    language: LanguageTag
    is_sandbox: IsSandboxConversation | None = None
    expected_starts_at: BookingStartsAtUnixSeconds | None = None


class CancelBookingCommand(ImmutableDTO):
    """
    Cancel a booking found by id, or by contact phone and date (sandbox
    rule as for rescheduling). `actor_id` names the staff member who
    cancels in the cabinet (they may undo it for a short while);
    `expected_starts_at` as for rescheduling.
    """

    business_id: BusinessId
    contact_id: ContactId | None = None
    booking_id: BookingId | None = None
    contact_phone_number: E164PhoneNumber | None = None
    date: LocalDate | None = None
    language: LanguageTag
    is_sandbox: IsSandboxConversation | None = None
    actor_id: UserId | None = None
    expected_starts_at: BookingStartsAtUnixSeconds | None = None


class BookingView(ImmutableDTO):
    """
    Booking rendered in the business time zone.

    `conversation_id` is the conversation it was made in (the assistant's
    tools, or staff booking from a conversation card). `language` is the
    customer's language for texts about it. `reminder_sent_at` is when the
    customer's reminder went out (None: not yet). A booking of a service,
    package or room type names it and carries its value (`value_minor` in
    `currency_code`).
    """

    id: BookingId
    business_id: BusinessId
    resource_id: ResourceId
    resource_name: ResourceName
    contact_id: ContactId
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    date: LocalDate
    time: LocalTimeOfDay | None = None
    end_date: LocalDate
    end_time: LocalTimeOfDay | None = None
    timezone: TimezoneName
    party_size: PartySize
    status: BookingStatus
    source_channel: ChannelKind
    notes: BookingNote | None = None
    is_sandbox: IsSandboxConversation = False
    conversation_id: ConversationId | None = None
    language: LanguageTag | None = None
    reminder_sent_at: Microseconds | None = None
    created_at: Microseconds
    service_item_id: KnowledgeItemId | None = None
    service_title: KnowledgeTitle | None = None
    value_minor: BookingValueMinor | None = None
    currency_code: CurrencyCode | None = None


class BookingResult(ImmutableDTO):
    """
    Booking plus a confirmation text in the customer's language
    (concept create_booking output: booking_id and confirmation text).
    """

    booking: BookingView
    confirmation_text: MessageText


class CreateLeadCommand(ImmutableDTO):
    """Create a request for a manager (concept create_lead)."""

    business_id: BusinessId
    contact_id: ContactId
    conversation_id: ConversationId | None = None
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    lead_type: LeadType
    details: LeadDetails
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None
    source_channel: ChannelKind
    language: LanguageTag
    is_sandbox: IsSandboxConversation = False


class LeadView(ImmutableDTO):
    """Lead as shown to staff."""

    id: LeadId
    business_id: BusinessId
    contact_id: ContactId
    lead_type: LeadType
    details: LeadDetails
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None
    source_channel: ChannelKind
    status: LeadStatus
    is_sandbox: IsSandboxConversation = False
