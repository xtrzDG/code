"""
Money in minor units survives the trip to major units and back in every
currency CLDR knows (0, 2, 3 and 4 decimals), and the identity operations
(times one, converted at rate one) change nothing.
"""

from decimal import ROUND_HALF_EVEN, Decimal

from babel.numbers import list_currencies
from hypothesis import given
from hypothesis import strategies as st

from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.constrained_strings import ExchangeRateValue
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.money.money_math import (
    build_money_from_major_units,
    convert_money,
    convert_money_to_major_units,
    get_currency_minor_unit_digits,
    multiply_money,
)

CURRENCIES: list[CurrencyCode] = [
    CurrencyCode(code) for code in sorted(list_currencies())
]
# Up to a trillion major units of the coarsest currency.
MAX_MINOR: int = 10**16

currencies = st.sampled_from(CURRENCIES)
amounts = st.integers(min_value=0, max_value=MAX_MINOR)


def money(amount: int, currency: CurrencyCode) -> Money:
    return Money(amount_minor=MoneyAmountMinor(amount), currency_code=currency)


def test_every_currency_has_a_known_precision() -> None:
    assert len(CURRENCIES) > 150
    assert {int(get_currency_minor_unit_digits(code)) for code in CURRENCIES} <= {
        0,
        2,
        3,
        4,
    }


@given(currencies, amounts)
def test_minor_units_survive_the_trip_through_major_units(
    currency: CurrencyCode, amount: int
) -> None:
    original = money(amount, currency)

    major = convert_money_to_major_units(original)

    assert build_money_from_major_units(major, currency) == original
    assert build_money_from_major_units(major, currency, ROUND_HALF_EVEN) == original
    digits = int(get_currency_minor_unit_digits(currency))
    assert major.as_tuple().exponent == -digits


@given(currencies, amounts)
def test_times_one_and_rate_one_change_nothing(
    currency: CurrencyCode, amount: int
) -> None:
    original = money(amount, currency)

    assert multiply_money(original, Decimal(1)) == original
    assert convert_money(original, ExchangeRateValue("1"), currency) == original


@given(currencies, amounts, st.integers(min_value=0, max_value=9))
def test_a_finer_amount_rounds_to_the_nearest_minor_unit(
    currency: CurrencyCode, amount: int, extra_digit: int
) -> None:
    digits = int(get_currency_minor_unit_digits(currency))
    # The amount plus a tenth of a minor unit times `extra_digit`.
    finer = Decimal(amount * 10 + extra_digit).scaleb(-(digits + 1))

    rounded = build_money_from_major_units(finer, currency)

    assert int(rounded.amount_minor) == amount + (1 if extra_digit >= 5 else 0)
