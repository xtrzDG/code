"""Busy periods: making one safely, keeping it in a window, merging overlaps."""

from collections.abc import Sequence

from app.schemas.dto.calendar_sync.busy_reads import BusyPeriod, BusyWindow
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)


def new_period(starts_at: int, ends_at: int) -> BusyPeriod | None:
    """The period [starts_at, ends_at); None when it is empty or before 1970."""

    if ends_at <= starts_at or starts_at < 0:
        return None

    return BusyPeriod(
        starts_at=BusyStartsAtUnixSeconds(starts_at),
        ends_at=BusyEndsAtUnixSeconds(ends_at),
    )


def clip_to_window(period: BusyPeriod, window: BusyWindow) -> BusyPeriod | None:
    """The part of the period inside the window; None when there is none."""

    return new_period(
        max(int(period.starts_at), int(window.starts_at)),
        min(int(period.ends_at), int(window.ends_at)),
    )


def merge_busy_periods(periods: Sequence[BusyPeriod]) -> list[BusyPeriod]:
    """Sorted, with overlapping and touching periods joined into one."""

    merged: list[tuple[int, int]] = []
    for period in sorted(periods, key=lambda item: int(item.starts_at)):
        start, end = int(period.starts_at), int(period.ends_at)
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    return [
        BusyPeriod(
            starts_at=BusyStartsAtUnixSeconds(start),
            ends_at=BusyEndsAtUnixSeconds(end),
        )
        for start, end in merged
    ]


def subtract_periods(
    busy: Sequence[BusyPeriod], taken_out: Sequence[tuple[int, int]]
) -> list[BusyPeriod]:
    """The busy periods without the [start, end) ranges taken out of them."""

    remaining: list[tuple[int, int]] = [
        (int(period.starts_at), int(period.ends_at)) for period in busy
    ]
    for cut_start, cut_end in taken_out:
        pieces: list[tuple[int, int]] = []
        for start, end in remaining:
            if cut_end <= start or end <= cut_start:
                pieces.append((start, end))
                continue
            if start < cut_start:
                pieces.append((start, cut_start))
            if cut_end < end:
                pieces.append((cut_end, end))
        remaining = pieces

    return [period for start, end in remaining if (period := new_period(start, end))]
