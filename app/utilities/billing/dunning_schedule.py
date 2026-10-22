"""
When the retries of a declined automatic charge are due: on days 1, 3 and
6 of the grace period (business-local calendar days after the decline,
at the time of day it was declined), before the grace period ends.
"""

from typed_time_provider import Microseconds

from app.schemas.typings.billing.constrained_integers import (
    PaymentRetryAttempt,
    PaymentRetryDayOffset,
)
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.billing.billing_periods import add_local_days

RETRY_SCHEDULE: tuple[tuple[PaymentRetryAttempt, PaymentRetryDayOffset], ...] = (
    (PaymentRetryAttempt(1), PaymentRetryDayOffset(1)),
    (PaymentRetryAttempt(2), PaymentRetryDayOffset(3)),
    (PaymentRetryAttempt(3), PaymentRetryDayOffset(6)),
)
LAST_RETRY_ATTEMPT: PaymentRetryAttempt = RETRY_SCHEDULE[-1][0]


def find_grace_start(
    grace_until: Microseconds, grace_days: int, timezone: TimezoneName
) -> Microseconds:
    """When the grace period began: its end, `grace_days` local days back."""

    return add_local_days(grace_until, -grace_days, timezone)


def retry_due_at(
    grace_start: Microseconds,
    attempt: PaymentRetryAttempt,
    timezone: TimezoneName,
) -> Microseconds:
    offset: PaymentRetryDayOffset = dict(RETRY_SCHEDULE)[attempt]
    return add_local_days(grace_start, int(offset), timezone)


def find_due_attempt(
    grace_start: Microseconds, now: Microseconds, timezone: TimezoneName
) -> PaymentRetryAttempt | None:
    """The latest retry due by now (an earlier one missed is not made)."""

    due: list[PaymentRetryAttempt] = [
        attempt
        for attempt, _ in RETRY_SCHEDULE
        if retry_due_at(grace_start, attempt, timezone) <= now
    ]
    return due[-1] if due else None


def find_next_retry_at(
    grace_start: Microseconds,
    after: PaymentRetryAttempt | None,
    timezone: TimezoneName,
) -> Microseconds | None:
    """When the retry after `after` (the first one when None) is due."""

    for attempt, _ in RETRY_SCHEDULE:
        if after is None or int(attempt) > int(after):
            return retry_due_at(grace_start, attempt, timezone)

    return None


def list_earlier_attempts(
    attempt: PaymentRetryAttempt,
) -> list[PaymentRetryAttempt]:
    return [earlier for earlier, _ in RETRY_SCHEDULE if int(earlier) < int(attempt)]
