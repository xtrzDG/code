"""
The reads of one resource's sources, ready to run within a window, and the
document a successful read is kept in.
"""

from collections.abc import Callable
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.facilitators.calendar_sync.booking_system_busy_reader import (
    BookingSystemBusyReader,
)
from app.facilitators.calendar_sync.google_busy_reader import GoogleBusyReader
from app.facilitators.calendar_sync.ical_busy_reader import IcalBusyReader
from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.calendar_sync import (
    BusyBlock,
    CalendarBusyTimesDocument,
    IcalImportFeed,
    ResourceCalendarLinkDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.busy_reads import BusyPeriod, BusyWindow
from app.schemas.typings.bookings.strings import ExternalCalendarId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.utilities.calendar_sync.busy_windows import DayBounds, whole_day_bounds
from app.utilities.calendar_sync.calendar_sync_keys import busy_times_id_of
from app.utilities.scheduling.nights import read_stay_times
from app.utilities.scheduling.zoned_time import load_time_zone

UTC_ZONE: ZoneInfo = ZoneInfo("UTC")

type BusyRead = Callable[[BusyWindow], list[BusyPeriod]]
type SourceRead = tuple[BusyTimeSource, IcalImportFeedId | None, BusyRead]


class BusyTimeReads:
    """The readers of the three kinds of source, and what a resource links."""

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        google: GoogleBusyReader,
        ical: IcalBusyReader,
        booking_systems: BookingSystemBusyReader,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self.google: GoogleBusyReader = google
        self.ical: IcalBusyReader = ical
        self.booking_systems: BookingSystemBusyReader = booking_systems

    def zone_of(self, business_id: BusinessId) -> ZoneInfo:
        business: BusinessDocument | None = self._business_repo.get(business_id)
        return UTC_ZONE if business is None else load_time_zone(business.timezone)

    def reads_of(
        self,
        resource: ResourceDocument,
        link: ResourceCalendarLinkDocument,
        zone: ZoneInfo,
        timeout: BusyTimeFetchSeconds,
    ) -> list[SourceRead]:
        """One read per linked source, in a fixed order."""

        reads: list[SourceRead] = []
        calendar_id: ExternalCalendarId | None = resource.external_calendar_id
        if calendar_id is not None and link.google_status is not None:
            reads.append(
                (
                    BusyTimeSource.GOOGLE,
                    None,
                    lambda window: self.google.read(
                        resource.business_id, calendar_id, window, timeout
                    ),
                )
            )

        if link.ical_imports:
            day_bounds: DayBounds = whole_day_bounds(
                resource,
                zone,
                read_stay_times(
                    self._business_profile_repo.get_by_business(resource.business_id)
                ),
            )
            reads.extend(
                (
                    BusyTimeSource.ICAL,
                    feed.feed_id,
                    self._feed_read(feed, zone, day_bounds, timeout),
                )
                for feed in link.ical_imports
            )

        booking_system = link.booking_system
        if booking_system is not None:
            reads.append(
                (
                    BusyTimeSource.BOOKING_SYSTEM,
                    None,
                    lambda window: self.booking_systems.read(
                        booking_system, window, timeout
                    ),
                )
            )

        return reads

    def _feed_read(
        self,
        feed: IcalImportFeed,
        zone: ZoneInfo,
        day_bounds: DayBounds,
        timeout: BusyTimeFetchSeconds,
    ) -> BusyRead:
        return lambda window: self.ical.read(feed, window, zone, day_bounds, timeout)


def busy_times_document(
    resource: ResourceDocument,
    source: BusyTimeSource,
    feed_id: IcalImportFeedId | None,
    periods: list[BusyPeriod],
    window: BusyWindow,
    now: Microseconds,
) -> CalendarBusyTimesDocument:
    return CalendarBusyTimesDocument(
        id=busy_times_id_of(resource.id, source, feed_id),
        business_id=resource.business_id,
        resource_id=resource.id,
        source=source,
        feed_id=feed_id,
        blocks=[
            BusyBlock(starts_at=period.starts_at, ends_at=period.ends_at)
            for period in periods
        ],
        covers_until=window.ends_at,
        fetched_at=now,
        created_at=now,
        updated_at=now,
    )
