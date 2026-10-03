"""
Bookings in the cabinet: the list, manual bookings, rescheduling and edits.

Model-tool DTOs (availability, create, cancel and reschedule a booking) live
in `app/schemas/dto/bookings.py`.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.bookings import BookingOrder, BookingStatus, ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class ListBookingsQuery(ImmutableDTO):
    """
    One page of the bookings of a business for the cabinet, filtered by the
    local start date (inclusive range in the business time zone), status
    and resource, ordered by start time (earliest first by default).
    """

    business_id: BusinessId
    actor_id: UserId
    date_from: LocalDate | None = None
    date_to: LocalDate | None = None
    status: BookingStatus | None = None
    resource_id: ResourceId | None = None
    include_sandbox: IsSandboxIncluded = False
    order: BookingOrder = BookingOrder.EARLIEST_FIRST
    page: PageRequest = PageRequest()


class BookingPage(ImmutableDTO):
    """One page of bookings; `next_cursor` is None on the last page."""

    items: list[BookingView] = Field(default_factory=list[BookingView])
    next_cursor: PageCursor | None = None


class ManualBookingRequest(ImmutableDTO):
    """
    Body of a booking added by staff in the cabinet.

    The phone may be typed in any national or international format; it is
    parsed with `country_hint` (the business country when omitted).
    `language` is the customer's language for the confirmation text
    (business default when omitted). `conversation_id` books for the
    customer of that conversation and links the booking to it.
    """

    contact_name: ContactName
    contact_phone_number: RawPhoneNumberInput | None = None
    resource_kind: ResourceKind | None = None
    resource_id: ResourceId | None = None
    date: LocalDate
    time: LocalTimeOfDay | None = None
    duration_minutes: BookingDurationMinutes | None = None
    nights: NightCount | None = None
    party_size: PartySize
    notes: BookingNote | None = None
    source_channel: ChannelKind = ChannelKind.PHONE
    language: LanguageTag | None = None
    country_hint: CountryCode | None = None
    conversation_id: ConversationId | None = None


class ManualBookingCommand(ImmutableDTO):
    """
    Booking added by staff. Capacity and opening hours are enforced; the
    online-booking limits (minimum notice, maximum party size) are not,
    because staff decide those case by case.
    """

    business_id: BusinessId
    actor_id: UserId
    contact_name: ContactName
    contact_phone_number: RawPhoneNumberInput | None = None
    resource_kind: ResourceKind | None = None
    resource_id: ResourceId | None = None
    date: LocalDate
    time: LocalTimeOfDay | None = None
    duration_minutes: BookingDurationMinutes | None = None
    nights: NightCount | None = None
    party_size: PartySize
    notes: BookingNote | None = None
    source_channel: ChannelKind = ChannelKind.PHONE
    language: LanguageTag | None = None
    country_hint: CountryCode | None = None
    conversation_id: ConversationId | None = None


class RescheduleBookingRequest(ImmutableDTO):
    """Body of a cabinet reschedule: new local date and (for slots) time."""

    new_date: LocalDate
    new_time: LocalTimeOfDay | None = None


class UpdateBookingRequest(ImmutableDTO):
    """
    Body of a cabinet booking change; omitted fields stay as they are.

    `status`: COMPLETED, NO_SHOW or CANCELLED, or CONFIRMED for a PENDING
    booking. `party_size` and `resource_id` must fit the booked time (the
    resource seats the party, is open and has a free unit then). An empty or blank
    `notes` text removes the notes. `contact_name` renames the customer.
    The time is changed by rescheduling.
    """

    status: BookingStatus | None = None
    party_size: PartySize | None = None
    resource_id: ResourceId | None = None
    notes: BookingNote | None = None
    contact_name: ContactName | None = None


class UpdateBookingCommand(ImmutableDTO):
    """Staff changes the status or the details of a booking."""

    business_id: BusinessId
    actor_id: UserId
    booking_id: BookingId
    status: BookingStatus | None = None
    party_size: PartySize | None = None
    resource_id: ResourceId | None = None
    notes: BookingNote | None = None
    contact_name: ContactName | None = None
