"""
What a resource's export feed carries: its own bookings that take its
time (real ones, not cancelled), and the busy times of its Google calendar
and booking system. Never what came from an imported feed: a calendar that
imports the feed must not get its own reservations back (they would keep
each other busy after a cancellation).
"""

from collections.abc import Sequence
from zoneinfo import ZoneInfo

from app.schemas.constants.bookings import BookingUnit
from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.calendar_sync import CalendarBusyTimesDocument
from app.schemas.domain.resources import ResourceDocument
from app.utilities.calendar_sync.ical_export_feed import ExportedBusyTime
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.zoned_time import to_local_moment

# At most this many events per feed (two years of a busy resource).
MAX_EXPORTED_EVENTS: int = 2000
EXPORTED_SOURCES: frozenset[BusyTimeSource] = frozenset(
    {BusyTimeSource.GOOGLE, BusyTimeSource.BOOKING_SYSTEM}
)


def exported_busy_times(
    resource: ResourceDocument,
    bookings: Sequence[BookingDocument],
    busy_times: Sequence[CalendarBusyTimesDocument],
    zone: ZoneInfo,
    now_seconds: int,
) -> list[ExportedBusyTime]:
    """The feed's events, by start, ending after now (at most 2,000)."""

    is_stay: bool = resource.booking_unit is BookingUnit.NIGHT
    events: list[tuple[int, ExportedBusyTime]] = [
        (int(booking.starts_at), booking_event(booking, is_stay, zone))
        for booking in bookings
        if booking.resource_id == resource.id
        and not booking.is_sandbox
        and booking.status in BLOCKING_BOOKING_STATUSES
        and int(booking.ends_at) > now_seconds
    ]
    events.extend(
        (
            int(block.starts_at),
            ExportedBusyTime(
                uid_key=f"busy-{document.source.value}-{resource.id}-"
                f"{int(block.starts_at)}-{int(block.ends_at)}",
                times=(int(block.starts_at), int(block.ends_at)),
                dates=None,
            ),
        )
        for document in busy_times
        if document.resource_id == resource.id and document.source in EXPORTED_SOURCES
        for block in document.blocks
        if int(block.ends_at) > now_seconds
    )
    events.sort(key=lambda event: event[0])
    return [event for _, event in events[:MAX_EXPORTED_EVENTS]]


def booking_event(
    booking: BookingDocument, is_stay: bool, zone: ZoneInfo
) -> ExportedBusyTime:
    """A stay as check-in to check-out dates; other bookings as exact times."""

    if is_stay:
        return ExportedBusyTime(
            uid_key=f"booking-{booking.id}",
            times=None,
            dates=(
                to_local_moment(int(booking.starts_at), zone).date(),
                to_local_moment(int(booking.ends_at), zone).date(),
            ),
        )

    return ExportedBusyTime(
        uid_key=f"booking-{booking.id}",
        times=(int(booking.starts_at), int(booking.ends_at)),
        dates=None,
    )
