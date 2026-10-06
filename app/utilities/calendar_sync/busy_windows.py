"""
When busy times are read and for how long ahead, and the times a whole-day
event of an imported calendar takes on a resource.
"""

from collections.abc import Callable
from datetime import date
from zoneinfo import ZoneInfo

from app.schemas.constants.bookings import BookingUnit
from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.busy_reads import BusyWindow
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.utilities.scheduling.nights import StayTimes
from app.utilities.scheduling.zoned_time import lenient_utc_seconds

SECONDS_PER_DAY: int = 24 * 60 * 60
# The sync job reads every linked source this often; a source not read for
# two periods is stale, and availability reads it again on the spot.
SYNC_INTERVAL_SECONDS: int = 5 * 60
STALE_AFTER_SECONDS: int = 2 * SYNC_INTERVAL_SECONDS
# A booking that began yesterday may still run: the window starts a day back.
LOOK_BACK_SECONDS: int = SECONDS_PER_DAY
# How far ahead each source is read: Google's free/busy answers for a
# limited range; rentals' calendars (Airbnb, Booking.com) a year and more.
HORIZON_DAYS: dict[BusyTimeSource, int] = {
    BusyTimeSource.GOOGLE: 60,
    BusyTimeSource.ICAL: 400,
    BusyTimeSource.BOOKING_SYSTEM: 180,
}
# At most this many busy times are kept per source (a year of daily events).
MAX_BUSY_PERIODS: int = 2000

type DayBounds = Callable[[date, date], tuple[int, int]]


def busy_window(now_seconds: int, source: BusyTimeSource) -> BusyWindow:
    """From a day back to the source's horizon ahead."""

    return BusyWindow(
        starts_at=BusyStartsAtUnixSeconds(max(now_seconds - LOOK_BACK_SECONDS, 0)),
        ends_at=BusyEndsAtUnixSeconds(
            now_seconds + HORIZON_DAYS[source] * SECONDS_PER_DAY
        ),
    )


def whole_day_bounds(
    resource: ResourceDocument, zone: ZoneInfo, stay_times: StayTimes
) -> DayBounds:
    """
    The times the dates [first, end) of a whole-day event take: for a
    resource booked by the night, check-in on the first date to check-out
    on the end date (a reservation from the 10th to the 13th leaves the
    10th's morning and the 13th's afternoon free, as stays turn over);
    otherwise the whole local days.
    """

    if resource.booking_unit is BookingUnit.NIGHT:

        def stay(first: date, end: date) -> tuple[int, int]:
            return (
                lenient_utc_seconds(first, stay_times.check_in_minute, zone),
                lenient_utc_seconds(end, stay_times.check_out_minute, zone),
            )

        return stay

    def whole_days(first: date, end: date) -> tuple[int, int]:
        return (
            lenient_utc_seconds(first, 0, zone),
            lenient_utc_seconds(end, 0, zone),
        )

    return whole_days
