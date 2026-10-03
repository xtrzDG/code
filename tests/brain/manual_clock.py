"""A wall clock whose time tests move by hand."""

from datetime import UTC, datetime, timedelta

from typed_time_provider import Microseconds, WallClock

# Thursday 2026-10-01 10:00 UTC = 14:00 in Tbilisi.
START_MOMENT: datetime = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
NANOSECONDS_PER_MICROSECOND: int = 1000


class ManualClock:
    """Wall clock whose time tests move by hand."""

    def __init__(self, start: datetime = START_MOMENT) -> None:
        self.moment: datetime = start

    def advance(self, delta: timedelta) -> None:
        self.moment += delta

    def now_nanoseconds(self) -> int:
        delta: timedelta = self.moment - datetime(1970, 1, 1, tzinfo=UTC)
        microseconds: int = (
            delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds
        )
        return microseconds * NANOSECONDS_PER_MICROSECOND

    def wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=self.now_nanoseconds,
        )
