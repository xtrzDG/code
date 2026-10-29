"""Exact rate arithmetic: decimal strings, one half-even rounding, no floats."""

from datetime import date
from decimal import Decimal

import pytest

from app.schemas.typings.billing.constrained_strings import (
    ExchangeRateDate,
    ExchangeRateValue,
)
from app.utilities.exchange_rates.rate_math import (
    build_rate,
    days_between,
    divide_rates,
    invert_rate,
    older_date,
    parse_rate_text,
    rate_day_number,
)


@pytest.mark.parametrize(
    ("amount", "stored"),
    [
        # Ties at the 13th digit go to the even 12th digit.
        ("0.0000000000025", "0.000000000002"),
        ("0.0000000000035", "0.000000000004"),
        ("1.2345678901225", "1.234567890122"),
        ("1.2345678901235", "1.234567890124"),
        ("2.95520000", "2.9552"),
        ("168.12", "168.12"),
    ],
)
def test_computed_rates_round_half_to_even_at_twelve_places(
    amount: str, stored: str
) -> None:
    assert str(build_rate(Decimal(amount))) == stored


@pytest.mark.parametrize(
    "amount", ["0", "-1.5", "0.0000000000004", "1e13", "NaN", "Infinity"]
)
def test_a_rate_must_be_a_positive_number_that_fits(amount: str) -> None:
    assert build_rate(Decimal(amount)) is None


def test_feed_texts_are_read_per_unit_without_binary_floats() -> None:
    assert str(parse_rate_text("0.6884", 100)) == "0.006884"
    assert str(parse_rate_text(" 2.9552 ")) == "2.9552"
    assert str(parse_rate_text("0.1", 3)) == "0.033333333333"
    assert parse_rate_text("2,9552") is None
    assert parse_rate_text("1.5", 0) is None
    assert parse_rate_text("inf") is None


def test_inverse_and_cross_rates() -> None:
    usd_in_lari = ExchangeRateValue("2.6045")
    euro_in_dollars = ExchangeRateValue("1.1351")
    euro_in_lari = ExchangeRateValue("2.9563")

    assert str(invert_rate(usd_in_lari)) == "0.383950854291"
    assert str(invert_rate(ExchangeRateValue("0.5"))) == "2"
    # USD -> GEL through the euro: (EUR -> GEL) / (EUR -> USD).
    assert str(divide_rates(euro_in_lari, euro_in_dollars)) == "2.604440137433"
    # An inverse rounds once; one that would not fit is refused.
    assert invert_rate(ExchangeRateValue("999999999999")) == ExchangeRateValue(
        "0.000000000001"
    )
    assert invert_rate(ExchangeRateValue("0.000000000001")) is None


def test_rate_days_sort_and_age() -> None:
    assert int(rate_day_number(ExchangeRateDate("2026-09-30"))) == 20260930
    assert days_between(ExchangeRateDate("2026-09-30"), date(2026, 10, 3)) == 3
    older = older_date(ExchangeRateDate("2026-10-03"), ExchangeRateDate("2026-10-02"))
    assert str(older) == "2026-10-02"


@pytest.mark.parametrize(
    "text", ["0", "0.0", "-1", "1.", ".5", "01.5", "1.1234567890123", "1e3"]
)
def test_the_stored_rate_text_is_a_plain_positive_decimal(text: str) -> None:
    with pytest.raises(ValueError):
        ExchangeRateValue(text)
