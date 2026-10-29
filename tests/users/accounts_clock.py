"""An adjustable clock for the accounts tests: time moves only when told to.

Expiry and retention are tested by advancing it instead of sleeping.
"""

from typed_time_provider import Microseconds, WallClock

START_UNIX_NANOSECONDS: int = 1_790_000_000_000_000_000
NANOSECONDS_PER_SECOND: int = 1_000_000_000
SECONDS_PER_DAY: int = 24 * 60 * 60


class AdjustableClock:
    """Unix time in nanoseconds that tests move forward explicitly."""

    def __init__(self, start_nanoseconds: int = START_UNIX_NANOSECONDS) -> None:
        self.nanoseconds: int = start_nanoseconds

    def read(self) -> int:
        return self.nanoseconds

    def advance(self, seconds: int) -> None:
        self.nanoseconds += seconds * NANOSECONDS_PER_SECOND

    def build_wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=self.read,
        )

    def now_microseconds(self) -> Microseconds:
        return Microseconds(self.nanoseconds // 1000)

    def microseconds_ago(self, seconds: int) -> Microseconds:
        return Microseconds((self.nanoseconds // 1000) - seconds * 1_000_000)
