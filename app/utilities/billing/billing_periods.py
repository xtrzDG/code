"""
Billing calendar arithmetic in the business time zone.

Months and days are added to the local wall-clock time and converted back
to UTC microseconds, so a period that starts at 10:00 in Tbilisi ends at
10:00 there, and a month from 31 January ends on the last day of February.
"""

import calendar
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.constants.billing import BillingPeriod
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.typings.billing.constrained_integers import BillingIntervalMonths
from app.schemas.typings.billing.constrained_strings import AutoDebitStartDate
from app.schemas.typings.localization.constrained_strings import TimezoneName

UNIX_EPOCH: datetime = datetime(1970, 1, 1, tzinfo=UTC)
ONE_MICROSECOND: timedelta = timedelta(microseconds=1)
MONTHS_IN_YEAR: int = 12
MAX_WINDOW_STEPS: int = 1200
INTERVAL_MONTHS_BY_PERIOD: dict[BillingPeriod, int] = {
    BillingPeriod.MONTHLY: 1,
    BillingPeriod.ANNUAL: MONTHS_IN_YEAR,
}


def to_local_datetime(instant: Microseconds, timezone: TimezoneName) -> datetime:
    """UTC microseconds -> aware local datetime in the IANA zone."""

    utc_moment: datetime = UNIX_EPOCH + timedelta(microseconds=int(instant))
    return utc_moment.astimezone(ZoneInfo(str(timezone)))


def to_microseconds(moment: datetime) -> Microseconds:
    """Aware datetime -> UTC microseconds since the epoch, exactly."""

    return Microseconds((moment.astimezone(UTC) - UNIX_EPOCH) // ONE_MICROSECOND)


def add_calendar_months(
    instant: Microseconds,
    months: int,
    timezone: TimezoneName,
) -> Microseconds:
    """Same local time `months` later; the day is clamped to the month length."""

    local_moment: datetime = to_local_datetime(instant, timezone)
    month_index: int = local_moment.month - 1 + months
    year: int = local_moment.year + month_index // MONTHS_IN_YEAR
    month: int = month_index % MONTHS_IN_YEAR + 1
    day: int = min(local_moment.day, calendar.monthrange(year, month)[1])
    shifted: datetime = local_moment.replace(year=year, month=month, day=day, fold=0)
    return to_microseconds(shifted)


def add_local_days(
    instant: Microseconds,
    days: int,
    timezone: TimezoneName,
) -> Microseconds:
    """Same local time `days` calendar days later (daylight saving aware)."""

    local_moment: datetime = to_local_datetime(instant, timezone)
    shifted_date = local_moment.date() + timedelta(days=days)
    shifted: datetime = local_moment.replace(
        year=shifted_date.year,
        month=shifted_date.month,
        day=shifted_date.day,
        fold=0,
    )
    return to_microseconds(shifted)


def get_interval_months(billing_period: BillingPeriod) -> BillingIntervalMonths:
    """1 for monthly, 12 for annual billing."""

    return BillingIntervalMonths(INTERVAL_MONTHS_BY_PERIOD[billing_period])


def add_billing_period(
    period_start: Microseconds,
    billing_period: BillingPeriod,
    timezone: TimezoneName,
) -> Microseconds:
    """End of the service period that starts at `period_start`."""

    return add_calendar_months(
        period_start,
        int(get_interval_months(billing_period)),
        timezone,
    )


def to_local_calendar_day(
    instant: Microseconds,
    timezone: TimezoneName,
) -> AutoDebitStartDate:
    """Local calendar day of an instant, "YYYY-MM-DD"."""

    return AutoDebitStartDate(to_local_datetime(instant, timezone).date().isoformat())


def find_usage_window(
    subscription: SubscriptionDocument,
    now: Microseconds,
    timezone: TimezoneName,
) -> tuple[Microseconds, Microseconds]:
    """
    Billing window that contains `now`.

    Within the stored period it is the period itself. After it (an unpaid
    or not yet renewed subscription) the windows continue back to back with
    the subscription's billing period, so usage keeps being metered.
    """

    window_start: Microseconds = subscription.period_start
    window_end: Microseconds = subscription.period_end
    for _ in range(MAX_WINDOW_STEPS):
        if now < window_end or window_end <= window_start:
            break

        window_start = window_end
        window_end = add_billing_period(
            window_start,
            subscription.billing_period,
            timezone,
        )

    return window_start, window_end
