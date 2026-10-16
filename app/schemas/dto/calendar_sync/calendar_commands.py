"""What the cabinet asks of a resource's calendars, and the bodies it sends."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.calendar_sync import BookingSystemKind, BusyTimeSource
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import ExternalCalendarId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_strings import (
    BookingSystemResourceId,
    CalendarFeedUrl,
)
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.schemas.typings.calendar_sync.strings import BookingSystemApiKey
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.users.prefixed_id import UserId


class ResourceCalendarQuery(ImmutableDTO):
    """A resource's calendars (owners and staff)."""

    business_id: BusinessId
    resource_id: ResourceId


class GoogleCalendarLinkRequest(ImmutableDTO):
    """The Google calendar (from the account's list, or its address) to link."""

    calendar_id: ExternalCalendarId


class LinkGoogleCalendarCommand(ImmutableDTO):
    business_id: BusinessId
    resource_id: ResourceId
    calendar_id: ExternalCalendarId
    actor_id: UserId


class IcalImportRequest(ImmutableDTO):
    """An iCal feed address to import (Airbnb, Booking.com, Vrbo, any)."""

    url: CalendarFeedUrl


class AddIcalImportCommand(ImmutableDTO):
    business_id: BusinessId
    resource_id: ResourceId
    url: CalendarFeedUrl
    actor_id: UserId


class BookingSystemLinkRequest(ImmutableDTO):
    """
    The booking system to follow: which one, what the resource is there
    (a Cal.com event type id) and the business's API key.
    """

    kind: BookingSystemKind
    external_resource_id: BookingSystemResourceId
    api_key: BookingSystemApiKey


class LinkBookingSystemCommand(ImmutableDTO):
    business_id: BusinessId
    resource_id: ResourceId
    link: BookingSystemLinkRequest
    actor_id: UserId


class RemoveCalendarSourceCommand(ImmutableDTO):
    """Stop a source blocking the resource (an iCal feed by its id)."""

    business_id: BusinessId
    resource_id: ResourceId
    source: BusyTimeSource
    feed_id: IcalImportFeedId | None = None
    actor_id: UserId


class IcalExportCommand(ImmutableDTO):
    """
    Make (or make again) or remove the resource's export address;
    `public_base_url` is this API's public origin, for the new address.
    """

    business_id: BusinessId
    resource_id: ResourceId
    actor_id: UserId
    public_base_url: PublicBaseUrl | None = None


class SyncResourceCalendarCommand(ImmutableDTO):
    """Read the resource's sources now (each within 2 s)."""

    business_id: BusinessId
    resource_id: ResourceId


class BusinessCalendarsQuery(ImmutableDTO):
    """A business's Google calendars to link, or its integrations."""

    business_id: BusinessId
