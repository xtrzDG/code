"""Shared constants and helpers of the storage tests."""

import itertools
from pathlib import Path

from typed_time_provider import Microseconds, WallClock

from app.contracts.storage import MigrationRetryPauseContract
from app.schemas.typings.storage.constrained_integers import MigrationAttemptNumber

MIGRATIONS_DIRECTORY: Path = Path(__file__).resolve().parents[2] / "migrations"
PROJECT_ROOT_DIRECTORY: Path = Path(__file__).resolve().parents[2]
FIXED_NANOSECONDS: int = 1_790_000_000_000_000_000
NANOSECONDS_PER_MICROSECOND: int = 1_000


def build_fixed_wall_clock(
    unix_nanoseconds: int = FIXED_NANOSECONDS,
) -> WallClock[Microseconds]:
    return WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: unix_nanoseconds,
    )


def build_ticking_wall_clock(
    step_microseconds: int = 1,
) -> WallClock[Microseconds]:
    """A clock that moves forward by `step_microseconds` on every reading."""

    readings = itertools.count(
        FIXED_NANOSECONDS,
        step_microseconds * NANOSECONDS_PER_MICROSECOND,
    )
    return WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: next(readings),
    )


class RecordedRetryPause(MigrationRetryPauseContract):
    """A migration retry pause that only records the tries it followed."""

    def __init__(self) -> None:
        self.attempts: list[int] = []

    def pause(self, attempt: MigrationAttemptNumber) -> None:
        self.attempts.append(int(attempt))
