from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.scheduling.zoned_time import (
    lenient_utc_seconds,
    load_time_zone,
    microseconds_to_seconds,
    to_local_date,
    to_local_moment,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
SECONDS_PER_MINUTE: int = 60
MINUTES_PER_HOUR: int = 60
SECONDS_PER_DAY: int = 24 * 60 * 60


class DemoClock:
    """
    Moments of the demo story, relative to the moment of seeding and read
    in the business time zone: "three days ago at 19:05", "tomorrow at
    20:00". A day offset of 0 is today; negative offsets are in the past.
    """

    def __init__(self, now: Microseconds, timezone: TimezoneName) -> None:
        self._now: Microseconds = now
        self._timezone: TimezoneName = timezone
        self._zone: ZoneInfo = load_time_zone(timezone)
        self._today: date = to_local_moment(
            microseconds_to_seconds(int(now)), self._zone
        ).date()

    @property
    def now(self) -> Microseconds:
        return self._now

    @property
    def timezone(self) -> TimezoneName:
        return self._timezone

    def at(self, day: int, clock: str) -> Microseconds:
        """Local wall time "HH:MM" on today + `day`."""

        hours, minutes = (int(part) for part in clock.split(":"))
        local_day: date = self._today + timedelta(days=day)
        utc_seconds: int = lenient_utc_seconds(
            local_day, hours * MINUTES_PER_HOUR + minutes, self._zone
        )
        return Microseconds(utc_seconds * MICROSECONDS_PER_SECOND)

    def past(self, day: int, clock: str) -> Microseconds:
        """Like `at`, a day earlier when that moment has not come yet."""

        moment: Microseconds = self.at(day, clock)
        return moment if moment < self._now else self.at(day - 1, clock)

    def upcoming(self, day: int, clock: str) -> Microseconds:
        """Like `at`, a day later when that moment has passed already."""

        moment: Microseconds = self.at(day, clock)
        return moment if moment > self._now else self.at(day + 1, clock)

    def ago(self, minutes: int = 0, hours: int = 0, days: int = 0) -> Microseconds:
        seconds: int = (
            minutes * SECONDS_PER_MINUTE
            + hours * MINUTES_PER_HOUR * SECONDS_PER_MINUTE
            + days * SECONDS_PER_DAY
        )
        return Microseconds(int(self._now) - seconds * MICROSECONDS_PER_SECOND)

    def later(self, moment: Microseconds, minutes: int) -> Microseconds:
        """`minutes` after a moment of the story."""

        return Microseconds(
            int(moment) + minutes * SECONDS_PER_MINUTE * MICROSECONDS_PER_SECOND
        )

    def next_slot(
        self,
        clocks: tuple[str, ...] = ("19:30", "20:00", "21:00", "13:00", "14:00"),
        notice_minutes: int = 90,
        within_hours: int = 22,
    ) -> Microseconds:
        """
        The first of `clocks` today or tomorrow that is at least
        `notice_minutes` away and within `within_hours`: a table "for
        tonight" when it is still early, otherwise lunch tomorrow.
        """

        earliest: int = int(self._now) + notice_minutes * 60 * MICROSECONDS_PER_SECOND
        latest: int = int(self._now) + within_hours * 3600 * MICROSECONDS_PER_SECOND
        candidates: list[Microseconds] = sorted(
            self.at(day, clock) for day in (0, 1) for clock in clocks
        )
        for moment in candidates:
            if earliest <= int(moment) <= latest:
                return moment

        return Microseconds(earliest)

    def next_weekday(self, weekday_index: int, clock: str) -> Microseconds:
        """The coming weekday (0 Monday ... 6 Sunday) after today, at `clock`."""

        days_ahead: int = (weekday_index - self._today.weekday()) % 7 or 7
        return self.at(days_ahead, clock)

    def last_weekday(self, weekday_index: int, clock: str) -> Microseconds:
        """The latest weekday (0 Monday ... 6 Sunday) before today, at `clock`."""

        days_back: int = (self._today.weekday() - weekday_index) % 7 or 7
        return self.at(-days_back, clock)

    def short_date(self, moment: Microseconds) -> str:
        """Local "DD.MM", as people write a date in a message."""

        return self.local_moment(moment).strftime("%d.%m")

    def clock_of(self, moment: Microseconds) -> str:
        """Local "HH:MM" of a moment."""

        return self.local_moment(moment).strftime("%H:%M")

    def days_from_today(self, moment: Microseconds) -> int:
        """0 for a moment today, 1 tomorrow, -1 yesterday."""

        return (self.local_moment(moment).date() - self._today).days

    def weekday_index(self, moment: Microseconds) -> int:
        """0 for Monday ... 6 for Sunday."""

        return self.local_moment(moment).weekday()

    def local_moment(self, moment: Microseconds) -> datetime:
        return to_local_moment(microseconds_to_seconds(int(moment)), self._zone)

    def date(self, day: int) -> LocalDate:
        """Local date today + `day`, "YYYY-MM-DD"."""

        return to_local_date(self._today + timedelta(days=day))

    def local_date_of(self, moment: Microseconds) -> LocalDate:
        return to_local_date(self.local_moment(moment).date())

    def booking_start(self, moment: Microseconds) -> BookingStartsAtUnixSeconds:
        return BookingStartsAtUnixSeconds(microseconds_to_seconds(int(moment)))

    def booking_end(
        self, moment: Microseconds, minutes: int
    ) -> BookingEndsAtUnixSeconds:
        return BookingEndsAtUnixSeconds(
            microseconds_to_seconds(int(moment)) + minutes * SECONDS_PER_MINUTE
        )
