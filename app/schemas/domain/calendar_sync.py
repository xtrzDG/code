"""
Two-way availability (migration 1160): the calendars outside the platform
that block a resource, what they made busy, and the resource's busy times
offered back as an iCal feed.
"""

from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.calendar_sync import (
    BookingSystemKind,
    BusyTimeSource,
    CalendarSyncProblem,
)
from app.schemas.typings.bookings.constrained_strings import CalendarSyncErrorSummary
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyBlockCount,
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.schemas.typings.calendar_sync.constrained_strings import (
    BookingSystemResourceId,
    CalendarFeedHost,
    IcalExportTokenHash,
)
from app.schemas.typings.calendar_sync.prefixed_id import (
    CalendarBusyTimesId,
    IcalExportFeedId,
    IcalImportFeedId,
    ResourceCalendarLinkId,
)
from app.schemas.typings.calendar_sync.strings import BookingSystemResourceTitle
from app.schemas.typings.channels.strings import EncryptedChannelSecret


class BusySourceStatus(PersistentDocument):
    """
    How one source of a resource synced: the last attempt, the last
    success with the number of busy times it brought, and the last
    failure's reason (cleared by the next success).
    """

    last_attempt_at: Microseconds | None = None
    last_synced_at: Microseconds | None = None
    block_count: BusyBlockCount = BusyBlockCount(0)
    problem: CalendarSyncProblem | None = None
    problem_detail: CalendarSyncErrorSummary | None = None


class IcalImportFeed(PersistentDocument):
    """
    An iCalendar feed a resource imports, and how it synced. The address is
    a secret (anyone with it reads the calendar), so it is stored
    encrypted; the cabinet shows only its host.
    """

    feed_id: IcalImportFeedId
    encrypted_url: EncryptedChannelSecret
    host: CalendarFeedHost
    added_at: Microseconds
    status: BusySourceStatus = Field(default_factory=BusySourceStatus)


class BookingSystemLink(PersistentDocument):
    """
    The booking system a resource follows: which system, what the resource
    is there (a Cal.com event type), the business's API key, encrypted,
    and how it synced.
    """

    kind: BookingSystemKind
    external_resource_id: BookingSystemResourceId
    external_resource_title: BookingSystemResourceTitle | None = None
    encrypted_api_key: EncryptedChannelSecret
    added_at: Microseconds
    status: BusySourceStatus = Field(default_factory=BusySourceStatus)


class ResourceCalendarLinkDocument(BaseDocument):
    """
    The calendar settings of one resource (one document per resource; its
    Google calendar is `ResourceDocument.external_calendar_id`): how that
    calendar synced, the iCal feeds it imports, the booking system it
    follows, the hash of its export address, and when the sync job reads
    its sources next (`next_sync_at`, None when nothing is linked).
    """

    id: ResourceCalendarLinkId
    business_id: BusinessId
    resource_id: ResourceId
    google_status: BusySourceStatus | None = None
    ical_imports: list[IcalImportFeed] = Field(default_factory=list[IcalImportFeed])
    booking_system: BookingSystemLink | None = None
    ical_export_token_hash: IcalExportTokenHash | None = None
    ical_export_created_at: Microseconds | None = None
    next_sync_at: Microseconds | None = None


class BusyBlock(PersistentDocument):
    """One busy time (UTC seconds) a source reported for a resource."""

    starts_at: BusyStartsAtUnixSeconds
    ends_at: BusyEndsAtUnixSeconds


class CalendarBusyTimesDocument(BaseDocument):
    """
    The cached busy times of one source of one resource (one imported feed
    for iCal: `feed_id`), as read at `fetched_at` for the window up to
    `covers_until`. A newer read replaces the whole list; an older read
    never overwrites a newer one. Every placement of a booking on the
    resource respects them.
    """

    id: CalendarBusyTimesId
    business_id: BusinessId
    resource_id: ResourceId
    source: BusyTimeSource
    feed_id: IcalImportFeedId | None = None
    blocks: list[BusyBlock] = Field(default_factory=list[BusyBlock])
    covers_until: BusyEndsAtUnixSeconds
    fetched_at: Microseconds


class IcalExportFeedDocument(BaseDocument):
    """
    A resource's busy times offered as an iCal feed at
    /v1/public/ical/{token}.ics. Stored by the hash of the token (the
    address is shown once); made again, the old address stops working.
    """

    id: IcalExportFeedId = Field(default_factory=IcalExportFeedId)
    business_id: BusinessId
    resource_id: ResourceId
    token_hash: IcalExportTokenHash
    last_read_at: Microseconds | None = None
