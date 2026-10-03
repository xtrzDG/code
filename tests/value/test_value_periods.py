"""Periods of reports, when they are due, and the typical check in other money."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.niches.niche_value_catalog import NICHE_VALUE_DEFAULTS
from app.registries.niches.niche_value_registry import NicheValueRegistry
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.value import ValueReportKind
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.value.typical_check import round_significant, typical_check_in
from app.utilities.value.value_periods import is_report_due, report_period

GEL: CurrencyCode = CurrencyCode("GEL")
EUR: CurrencyCode = CurrencyCode("EUR")


@pytest.mark.parametrize(
    ("kind", "today", "key", "first", "last"),
    [
        (
            ValueReportKind.DAILY,
            date(2026, 10, 1),
            "2026-09-30",
            "2026-09-30",
            "2026-09-30",
        ),
        (
            ValueReportKind.WEEKLY,
            date(2026, 10, 5),
            "2026-W40",
            "2026-09-28",
            "2026-10-04",
        ),
        # The first days of January belong to the last ISO week of the year.
        (
            ValueReportKind.WEEKLY,
            date(2027, 1, 4),
            "2026-W53",
            "2026-12-28",
            "2027-01-03",
        ),
        (
            ValueReportKind.MONTHLY,
            date(2027, 1, 1),
            "2026-12",
            "2026-12-01",
            "2026-12-31",
        ),
        (
            ValueReportKind.MONTHLY,
            date(2026, 3, 1),
            "2026-02",
            "2026-02-01",
            "2026-02-28",
        ),
    ],
)
def test_each_report_summarizes_the_period_just_over(
    kind: ValueReportKind, today: date, key: str, first: date | str, last: str
) -> None:
    period = report_period(kind, today)

    assert period.period_key == key
    assert (period.dates.date_from.isoformat(), period.dates.date_to.isoformat()) == (
        first,
        last,
    )


def test_the_month_before_a_month_is_the_whole_month_before() -> None:
    period = report_period(ValueReportKind.MONTHLY, date(2026, 3, 15))

    assert (period.dates.previous_from, period.dates.previous_to) == (
        date(2026, 1, 1),
        date(2026, 1, 31),
    )


@pytest.mark.parametrize(
    ("kind", "local_now", "is_due"),
    [
        (ValueReportKind.DAILY, "2026-10-06T08:59", False),
        (ValueReportKind.DAILY, "2026-10-06T09:00", True),
        (ValueReportKind.WEEKLY, "2026-10-05T08:59", False),
        (ValueReportKind.WEEKLY, "2026-10-05T09:00", True),
        (ValueReportKind.WEEKLY, "2026-10-07T03:00", True),
        (ValueReportKind.MONTHLY, "2026-11-01T08:00", False),
        (ValueReportKind.MONTHLY, "2026-11-01T09:30", True),
        (ValueReportKind.MONTHLY, "2026-11-02T00:10", True),
    ],
)
def test_reports_go_out_from_nine_in_the_morning(
    kind: ValueReportKind, local_now: str, is_due: bool
) -> None:
    assert is_report_due(kind, datetime.fromisoformat(local_now)) is is_due


@pytest.mark.parametrize(
    ("amount", "rounded"),
    [("118.21", "120"), ("0.4", "1"), ("9.6", "10"), ("1234", "1200"), ("5", "5")],
)
def test_converted_checks_round_like_prices_people_say(
    amount: str, rounded: str
) -> None:
    assert round_significant(Decimal(amount)) == Decimal(rounded)


def test_the_typical_check_is_converted_only_with_an_official_rate() -> None:
    forty_euro = Money(amount_minor=MoneyAmountMinor(4_000), currency_code=EUR)
    rates = ExchangeRateRegistry()

    assert typical_check_in(forty_euro, GEL, rates.find_rate(EUR, GEL)) == 12_000
    assert typical_check_in(forty_euro, EUR, None) == 4_000
    assert typical_check_in(forty_euro, CurrencyCode("USD"), None) is None
    assert (
        typical_check_in(forty_euro, CurrencyCode("USD"), rates.find_rate(EUR, GEL))
        is None
    )
    assert typical_check_in(None, GEL, rates.find_rate(EUR, GEL)) is None


def test_every_niche_has_its_estimates_once() -> None:
    registry = NicheValueRegistry()

    assert {registry.get(key).niche_key for key in NicheKey} == set(NicheKey)
    with pytest.raises(ValueError, match="two value entries"):
        NicheValueRegistry((*NICHE_VALUE_DEFAULTS, NICHE_VALUE_DEFAULTS[0]))
    with pytest.raises(ValueError, match="without value estimates"):
        NicheValueRegistry(NICHE_VALUE_DEFAULTS[1:])
