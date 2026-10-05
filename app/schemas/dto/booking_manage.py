"""
A guest's written confirmation of a booking and the page its link opens
(/r/{token}): what the link proves, what the page shows and what the guest
may change there without chatting.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import (
    BookingConfirmationChange,
    BookingStatus,
    BookingUnit,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.widget import WidgetContactLinkView
from app.schemas.typings.bookings.booleans import (
    CanCancelManagedBooking,
    CanRescheduleManagedBooking,
    IsBookingConfirmationQueued,
    IsManagedBookingOver,
    IsManagedStayAvailable,
    IsOpenOnDate,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import (
    BookingCalendarFileName,
    BookingManageLink,
    BookingManageToken,
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.bookings.strings import (
    BookingCalendarText,
    CalendarEventDescription,
    CalendarEventTitle,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import AddressText, BusinessName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.profiles.strings import CancellationPolicyText


class BookingManageClaims(ImmutableDTO):
    """
    What a manage link proves: the platform issued it for this booking of
    this business while the booking started at `booking_version` (a moved
    booking gets a new link), and it opens until `expires_at`.
    """

    business_id: BusinessId
    booking_id: BookingId
    booking_version: BookingStartsAtUnixSeconds
    expires_at: Microseconds


class BookingConfirmationRequest(ImmutableDTO):
    """
    Confirm a booking to its guest in writing, in the chat it was made in
    (the booking's conversation). `language` is the guest's language now;
    without it the booking's language, else the business's default one.
    """

    business_id: BusinessId
    booking_id: BookingId
    change: BookingConfirmationChange
    language: LanguageTag | None = None


class BookingConfirmationReceipt(ImmutableDTO):
    """
    Whether the confirmation went on its way (the widget shows it at once,
    a messenger gets it through the outbox) and the link it carries.
    """

    is_queued: IsBookingConfirmationQueued
    channel: ChannelKind | None = None
    manage_link: BookingManageLink | None = None


class ManagedBookingRequest(ImmutableDTO):
    """
    A guest's request through a manage link: the token from the address,
    and for a move (or the free times of a day) the new local date and
    time. The client address counts against the public rate limits.
    """

    token: BookingManageToken
    date: LocalDate | None = None
    time: LocalTimeOfDay | None = None
    client_ip_address: ClientIpAddress | None = None


class ManagedBookingAction(ImmutableDTO):
    """A manage request whose link checked out: the claims and the request."""

    business_id: BusinessId
    claims: BookingManageClaims
    date: LocalDate | None = None
    time: LocalTimeOfDay | None = None
    client_ip_address: ClientIpAddress | None = None


class RescheduleManagedBookingBody(ImmutableDTO):
    """The new local date, and the time for bookings of a time slot."""

    date: LocalDate
    time: LocalTimeOfDay | None = None


class ManagedBookingView(ImmutableDTO):
    """
    The guest's booking as the manage page shows it, in the business's
    time zone: no contact details of the guest (anyone holding the link
    sees the page). `token` is the link's current token (a move issues a
    new one); `language` is the guest's. `chat_links` are the ways to write
    to the business, the chat the booking was made in first.
    """

    token: BookingManageToken
    business_name: BusinessName
    status: BookingStatus
    booking_unit: BookingUnit
    date: LocalDate
    time: LocalTimeOfDay | None = None
    end_date: LocalDate
    end_time: LocalTimeOfDay | None = None
    timezone: TimezoneName
    party_size: PartySize
    service_title: KnowledgeTitle | None = None
    address: AddressText | None = None
    maps_url: WebLink | None = None
    phone_number: E164PhoneNumber | None = None
    cancellation_policy: CancellationPolicyText | None = None
    language: LanguageTag
    chat_links: list[WidgetContactLinkView] = Field(
        default_factory=list[WidgetContactLinkView]
    )
    can_cancel: CanCancelManagedBooking = False
    can_reschedule: CanRescheduleManagedBooking = False
    is_over: IsManagedBookingOver = False


class ManagedBookingSlots(ImmutableDTO):
    """
    When the booking could move to on one local date: the free start times
    of a time-slot booking (its length, party and service as booked), or
    for a stay whether its nights are free from that date (`times` empty).
    """

    date: LocalDate
    timezone: TimezoneName
    booking_unit: BookingUnit
    is_open_on_date: IsOpenOnDate
    times: list[LocalTimeOfDay] = Field(default_factory=list[LocalTimeOfDay])
    is_stay_available: IsManagedStayAvailable = False


class BookingCalendarFile(ImmutableDTO):
    """An .ics file of the booking for the guest's calendar."""

    file_name: BookingCalendarFileName
    content: BookingCalendarText


class BookingCalendarEvent(ImmutableDTO):
    """
    What a guest's calendar file says about the booking, its texts already
    in the guest's language: the times in UTC, `changed_at` (the booking's
    last change, which orders the file's versions) and the manage link.
    """

    booking_id: BookingId
    starts_at: BookingStartsAtUnixSeconds
    ends_at: BookingEndsAtUnixSeconds
    stamped_at: Microseconds
    changed_at: Microseconds
    title: CalendarEventTitle
    description: CalendarEventDescription
    location: AddressText | None = None
    url: BookingManageLink | None = None
    status: BookingStatus
