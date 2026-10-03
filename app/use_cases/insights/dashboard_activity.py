"""
The dashboard's counts, folded from the grouped counts the database
returns (no conversation, message, booking or handoff is read).
"""

from collections import Counter
from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field

from app.schemas.dto.operations.activity_counts import (
    BookingActivityCount,
    ConversationMixCount,
    ConversationTimelineCount,
    HandoffActivityCount,
)
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.use_cases.insights.dashboard_timeline import TimelineStretch


def ranked_counts[Key: Hashable](
    counts: Iterable[tuple[Key, int]],
) -> list[tuple[Key, PeriodItemCount]]:
    """Totals per key, largest first (ties in key order)."""

    totals: Counter[Key] = Counter()
    for key, count in counts:
        totals[key] += count

    return [
        (key, PeriodItemCount(total))
        for key, total in sorted(
            totals.items(), key=lambda item: (-item[1], str(item[0]))
        )
        if total > 0
    ]


@dataclass(frozen=True)
class DailyCounts:
    """Counts per local day of the period (day index from 0)."""

    by_day: Counter[int] = field(default_factory=Counter[int])

    def on(self, day: int) -> PeriodItemCount:
        return PeriodItemCount(self.by_day[day])


@dataclass(frozen=True)
class ConversationActivity:
    total: int
    after_hours: int
    daily: DailyCounts


def fold_conversations(
    mix: list[ConversationMixCount],
    timeline: list[ConversationTimelineCount],
    stretches: list[TimelineStretch],
) -> ConversationActivity:
    """
    How many conversations started, per day, and after hours: flagged by
    the conversation engine, or started in a closed stretch of the day.
    """

    daily: Counter[int] = Counter()
    after_hours: int = 0
    for group in timeline:
        stretch: TimelineStretch = stretches[int(group.segment)]
        daily[stretch.day] += int(group.count)
        if group.is_after_hours or not stretch.is_open:
            after_hours += int(group.count)

    return ConversationActivity(
        total=sum(int(group.count) for group in mix),
        after_hours=after_hours,
        daily=DailyCounts(by_day=daily),
    )


def daily_bookings(counts: list[BookingActivityCount]) -> DailyCounts:
    daily: Counter[int] = Counter()
    for group in counts:
        daily[int(group.segment)] += int(group.count)

    return DailyCounts(by_day=daily)


def daily_handoffs(counts: list[HandoffActivityCount]) -> DailyCounts:
    daily: Counter[int] = Counter()
    for group in counts:
        daily[int(group.segment)] += int(group.count)

    return DailyCounts(by_day=daily)
