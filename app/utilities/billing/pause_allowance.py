"""
How many months a business may pause: whole months from the end of the
paid period, at most the cap in any rolling window (four in twelve).

A pause is known from its steps: PAUSE_SCHEDULED names its start and its
planned end, a RESUMED step of the same pause the end it really had (now,
the end of a paid pause month, or the planned end). A pause called off
before its start counts nothing; one ended early counts the months it
began.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.subscription_lifecycle import SubscriptionEventKind
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.billing.billing_periods import add_calendar_months

# A pause never runs longer than this many months (the cap is lower).
LONGEST_PAUSE_MONTHS: int = 12


def pause_spans(
    events: Sequence[SubscriptionEventDocument],
) -> list[tuple[Microseconds, Microseconds]]:
    """
    Each pause of the business as (start, end it really had or will
    have), from its steps in time order: a pause scheduled again from the
    same start replaces the open one, and the first RESUMED step closes it.
    """

    open_ends: dict[int, Microseconds] = {}
    spans: list[tuple[Microseconds, Microseconds]] = []
    for event in sorted(events, key=lambda step: int(step.occurred_at)):
        if event.pause_starts_at is None or event.pause_until is None:
            continue

        start: int = int(event.pause_starts_at)
        if event.kind is SubscriptionEventKind.PAUSE_SCHEDULED:
            open_ends[start] = event.pause_until
        elif event.kind is SubscriptionEventKind.RESUMED and start in open_ends:
            planned: Microseconds = open_ends.pop(start)
            end: int = max(start, min(int(planned), int(event.pause_until)))
            spans.append((event.pause_starts_at, Microseconds(end)))

    spans.extend((Microseconds(start), end) for start, end in open_ends.items())
    return spans


def paused_month_starts(
    spans: Sequence[tuple[Microseconds, Microseconds]],
    timezone: TimezoneName,
) -> list[Microseconds]:
    """The first moment of every month the pauses began, in time order."""

    starts: list[Microseconds] = []
    for start, end in spans:
        for month in range(LONGEST_PAUSE_MONTHS):
            month_start: Microseconds = add_calendar_months(start, month, timezone)
            if month_start >= end:
                break

            starts.append(month_start)

    return sorted(starts, key=int)


def count_paused_months(
    month_starts: Sequence[Microseconds],
    window_start: Microseconds,
    window_end: Microseconds,
) -> int:
    """Paused months that began in [window_start, window_end)."""

    return sum(
        1
        for month_start in month_starts
        if int(window_start) <= int(month_start) < int(window_end)
    )


def max_pause_months(
    events: Sequence[SubscriptionEventDocument],
    starts_at: Microseconds,
    timezone: TimezoneName,
    cap_months: int,
    window_months: int,
) -> int:
    """
    The longest pause from `starts_at` that keeps every `window_months`
    window within `cap_months` paused months (0 when none fits). The
    window that ends with the new pause is the fullest one, as pauses only
    lie behind it.
    """

    earlier: list[Microseconds] = paused_month_starts(pause_spans(events), timezone)
    for months in range(cap_months, 0, -1):
        new_end: Microseconds = add_calendar_months(starts_at, months, timezone)
        window_start: Microseconds = add_calendar_months(
            new_end, -window_months, timezone
        )
        used: int = count_paused_months(earlier, window_start, starts_at)
        if used + months <= cap_months:
            return months

    return 0


def months_paused_before(
    events: Sequence[SubscriptionEventDocument],
    moment: Microseconds,
    timezone: TimezoneName,
    window_months: int,
) -> int:
    """Paused months that began in the `window_months` before `moment`."""

    return count_paused_months(
        paused_month_starts(pause_spans(events), timezone),
        add_calendar_months(moment, -window_months, timezone),
        moment,
    )
