from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    BillingPeriod,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    TimezoneName,
)
from app.utilities.billing.billing_periods import (
    add_billing_period,
    add_calendar_months,
    add_local_days,
    find_usage_window,
    get_interval_months,
    to_local_calendar_day,
    to_local_datetime,
    to_microseconds,
)

HOUR: int = 60 * 60 * 1_000_000
DAY: int = 24 * HOUR


def local(
    timezone: str,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
) -> Microseconds:
    return to_microseconds(
        datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(timezone))
    )


def build_subscription(
    period_start: Microseconds,
    period_end: Microseconds,
    billing_period: BillingPeriod = BillingPeriod.MONTHLY,
) -> SubscriptionDocument:
    return SubscriptionDocument(
        business_id=BusinessId(),
        plan_key=PlanKey.CHAT,
        billing_period=billing_period,
        price_minor=MoneyAmountMinor(29300),
        currency_code=CurrencyCode("GEL"),
        status=SubscriptionStatus.ACTIVE,
        period_start=period_start,
        period_end=period_end,
    )


def test_microseconds_round_trip_through_local_time() -> None:
    instant = Microseconds(1_790_845_200_123_456)

    moment: datetime = to_local_datetime(instant, TimezoneName("Asia/Tbilisi"))

    assert moment.hour == 13
    assert moment.microsecond == 123_456
    assert to_microseconds(moment) == instant


@pytest.mark.parametrize(
    ("start", "expected"),
    [
        ((2026, 1, 31, 10, 0), (2026, 2, 28, 10, 0)),
        ((2028, 1, 31, 10, 0), (2028, 2, 29, 10, 0)),
        ((2026, 12, 15, 23, 30), (2027, 1, 15, 23, 30)),
        ((2026, 10, 31, 0, 0), (2026, 11, 30, 0, 0)),
    ],
)
def test_a_month_later_clamps_the_day_in_local_time(
    start: tuple[int, ...],
    expected: tuple[int, ...],
) -> None:
    timezone = TimezoneName("Asia/Tbilisi")

    assert add_calendar_months(local("Asia/Tbilisi", *start), 1, timezone) == local(
        "Asia/Tbilisi", *expected
    )


def test_a_month_across_daylight_saving_keeps_the_local_hour() -> None:
    timezone = TimezoneName("Europe/Rome")
    start: Microseconds = local("Europe/Rome", 2026, 3, 15, 9, 0)

    end: Microseconds = add_calendar_months(start, 1, timezone)

    assert to_local_datetime(end, timezone).hour == 9
    assert int(end) - int(start) == 31 * DAY - HOUR


def test_local_days_follow_daylight_saving() -> None:
    rome = TimezoneName("Europe/Rome")
    new_york = TimezoneName("America/New_York")

    spring = add_local_days(local("Europe/Rome", 2026, 3, 28, 12, 0), 1, rome)
    autumn = add_local_days(local("America/New_York", 2026, 10, 31, 12, 0), 7, new_york)

    assert int(spring) - int(local("Europe/Rome", 2026, 3, 28, 12, 0)) == 23 * HOUR
    assert to_local_datetime(autumn, new_york).hour == 12
    assert int(autumn) - int(local("America/New_York", 2026, 10, 31, 12, 0)) == (
        7 * DAY + HOUR
    )


def test_billing_periods_are_one_or_twelve_months() -> None:
    timezone = TimezoneName("Asia/Tokyo")
    start: Microseconds = local("Asia/Tokyo", 2026, 10, 1, 9, 0)

    assert int(get_interval_months(BillingPeriod.MONTHLY)) == 1
    assert int(get_interval_months(BillingPeriod.ANNUAL)) == 12
    assert add_billing_period(start, BillingPeriod.MONTHLY, timezone) == local(
        "Asia/Tokyo", 2026, 11, 1, 9, 0
    )
    assert add_billing_period(start, BillingPeriod.ANNUAL, timezone) == local(
        "Asia/Tokyo", 2027, 10, 1, 9, 0
    )


def test_calendar_day_is_local_to_the_business() -> None:
    instant: Microseconds = local("UTC", 2026, 10, 31, 22, 30)

    assert to_local_calendar_day(instant, TimezoneName("Pacific/Auckland")) == (
        "2026-11-01"
    )
    assert to_local_calendar_day(instant, TimezoneName("America/Los_Angeles")) == (
        "2026-10-31"
    )


def test_usage_window_is_the_period_or_continues_after_it() -> None:
    timezone = TimezoneName("Asia/Tbilisi")
    start: Microseconds = local("Asia/Tbilisi", 2026, 9, 1, 0, 0)
    end: Microseconds = local("Asia/Tbilisi", 2026, 10, 1, 0, 0)
    subscription = build_subscription(start, end)

    inside = find_usage_window(subscription, Microseconds(int(start) + DAY), timezone)
    later = find_usage_window(
        subscription,
        local("Asia/Tbilisi", 2026, 11, 20, 0, 0),
        timezone,
    )

    assert inside == (start, end)
    assert later == (
        local("Asia/Tbilisi", 2026, 11, 1, 0, 0),
        local("Asia/Tbilisi", 2026, 12, 1, 0, 0),
    )


def test_usage_window_of_an_empty_period_does_not_loop() -> None:
    instant: Microseconds = local("UTC", 2026, 10, 1, 0, 0)
    subscription = build_subscription(instant, instant)

    assert find_usage_window(
        subscription,
        Microseconds(int(instant) + DAY),
        TimezoneName("UTC"),
    ) == (instant, instant)
