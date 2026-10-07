"""
The game days' clock: every process of the world (the test, the API, the
worker) reads the same offset from one file and adds it to the real time,
so the test moves time forward for all of them at once ("six minutes
later") while every timer, lease and periodic job runs its real code.
"""

import os
import time
from pathlib import Path

from typed_time_provider import Microseconds, MonotonicClock, Nanoseconds, WallClock

CLOCK_FILE_VARIABLE: str = "CHAOS_CLOCK_FILE"
NANOSECONDS_PER_SECOND: int = 1_000_000_000


def read_offset_nanoseconds(path: Path) -> int:
    """The offset the test set (0 before it moved the clock)."""

    try:
        return int(float(path.read_text(encoding="utf-8")) * NANOSECONDS_PER_SECOND)
    except OSError, ValueError:
        return 0


class ChaosClock:
    """The test's handle on the shared offset."""

    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self._offset_seconds: float = 0.0
        self._write()

    def advance(self, seconds: float) -> None:
        """Every process of the world is `seconds` later from now on."""

        self._offset_seconds += seconds
        self._write()

    def now_seconds(self) -> float:
        return time.time() + self._offset_seconds

    def _write(self) -> None:
        # Replaced in one rename: a process never reads half a number.
        staging = self.path.with_suffix(".next")
        staging.write_text(f"{self._offset_seconds:.6f}", encoding="utf-8")
        os.replace(staging, self.path)


def shifted_wall_clock(path: Path) -> WallClock[Microseconds]:
    return WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: time.time_ns() + read_offset_nanoseconds(path),
    )


def shifted_nanosecond_wall_clock(path: Path) -> WallClock[Nanoseconds]:
    return WallClock(
        preferred_time_unit_type=Nanoseconds,
        unix_nanosecond_factory=lambda: time.time_ns() + read_offset_nanoseconds(path),
    )


def shifted_monotonic_clock(path: Path) -> MonotonicClock[Nanoseconds]:
    """Breakers and pauses count the moved time too."""

    return MonotonicClock(
        preferred_time_unit_type=Nanoseconds,
        monotonic_nanosecond_factory=lambda: (
            time.monotonic_ns() + read_offset_nanoseconds(path)
        ),
    )
