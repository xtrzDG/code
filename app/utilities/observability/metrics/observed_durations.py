"""
Durations measured for metrics, as `ObservedSeconds`: never negative (a
clock that went backwards counts as no wait) and capped at a year.
"""

from app.schemas.typings.observability.constrained_floats import ObservedSeconds

MICROSECONDS_PER_SECOND: float = 1_000_000.0
MILLISECONDS_PER_SECOND: float = 1_000.0
# A year: ObservedSeconds' upper bound.
LONGEST_OBSERVED_SECONDS: float = 31_536_000.0


def observed_seconds(seconds: float) -> ObservedSeconds:
    """A measured number of seconds, clamped to what a metric records."""

    return ObservedSeconds(min(LONGEST_OBSERVED_SECONDS, max(0.0, seconds)))


def seconds_between_microseconds(started: int, finished: int) -> ObservedSeconds:
    """From one Unix time in microseconds to a later one."""

    return observed_seconds((finished - started) / MICROSECONDS_PER_SECOND)


def milliseconds_as_seconds(milliseconds: int) -> ObservedSeconds:
    return observed_seconds(milliseconds / MILLISECONDS_PER_SECOND)
