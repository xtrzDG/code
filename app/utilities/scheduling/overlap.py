"""Overlap counting of bookings on identical units of a resource."""

from collections.abc import Sequence
from typing import NamedTuple


class BusyRange(NamedTuple):
    """UTC seconds during which one unit of a resource is taken."""

    starts_at: int
    ends_at: int


def max_concurrent_overlap(
    busy: Sequence[BusyRange], starts_at: int, ends_at: int
) -> int:
    """
    Largest number of busy ranges that overlap at one instant of
    [starts_at, ends_at).

    Units of a resource are identical and assigned later, so a new booking
    fits exactly when this peak is below the unit count (interval scheduling:
    the peak overlap equals the number of units needed). Touching ranges
    (one ends when the next starts) do not overlap.
    """

    events: list[tuple[int, int]] = []
    for busy_range in busy:
        overlap_start: int = max(busy_range.starts_at, starts_at)
        overlap_end: int = min(busy_range.ends_at, ends_at)
        if overlap_start < overlap_end:
            events.append((overlap_start, 1))
            events.append((overlap_end, -1))

    events.sort()
    current: int = 0
    peak: int = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)

    return peak


def has_free_unit(
    busy: Sequence[BusyRange],
    starts_at: int,
    ends_at: int,
    unit_count: int,
) -> bool:
    return max_concurrent_overlap(busy, starts_at, ends_at) < unit_count
