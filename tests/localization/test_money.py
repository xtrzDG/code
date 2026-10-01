from decimal import Decimal

import pytest

from app.schemas.dto.billing import Money
from app.schemas.exceptions.application_errors import (
    UnsupportedLanguageError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_floats import ExchangeRate
from app.schemas.typings.billing.constrained_integers import (
    CurrencyMinorUnitDigits,
    DiscountPercent,
    MoneyAmountMinor,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import FormattedMoneyText
from app.utilities.money.money_formatting import format_money
from app.utilities.money.money_math import (
    build_discount_factor,
    build_money_from_major_units,
    convert_money,
    convert_money_to_major_units,
    get_currency_minor_unit_digits,
    multiply_money,
)


def money(amount_minor: int, currency_code: str) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(amount_minor),
        currency_code=CurrencyCode(currency_code),
    )


@pytest.mark.parametrize(
    ("currency_code", "digits"),
    [
        ("EUR", 2),
        ("GEL", 2),
        ("USD", 2),
        ("JPY", 0),
        ("KRW", 0),
        ("KWD", 3),
        ("BHD", 3),
    ],
)
def test_minor_unit_digits_come_from_cldr(currency_code: str, digits: int) -> None:
    minor_unit_digits = get_currency_minor_unit_digits(CurrencyCode(currency_code))

    assert minor_unit_digits == digits
    assert type(minor_unit_digits) is CurrencyMinorUnitDigits


@pytest.mark.parametrize(
    ("amount_minor", "currency_code", "major_units"),
    [
        (51700, "GEL", Decimal("517.00")),
        (15, "EUR", Decimal("0.15")),
        (1234, "JPY", Decimal("1234")),
        (1234, "KWD", Decimal("1.234")),
        (0, "USD", Decimal("0.00")),
    ],
)
def test_minor_and_major_units_round_trip(
    amount_minor: int,
    currency_code: str,
    major_units: Decimal,
) -> None:
    original = money(amount_minor, currency_code)

    assert convert_money_to_major_units(original) == major_units
    assert build_money_from_major_units(major_units, CurrencyCode(currency_code)) == (
        original
    )


@pytest.mark.parametrize(
    ("major_units", "currency_code", "expected_minor"),
    [
        (Decimal("0.44328"), "GEL", 44),
        (Decimal("0.005"), "EUR", 1),
        (Decimal("0.0049"), "EUR", 0),
        (Decimal("2.5"), "JPY", 3),
        (Decimal("1.2345"), "KWD", 1235),
    ],
)
def test_rounding_is_half_up_to_currency_precision(
    major_units: Decimal,
    currency_code: str,
    expected_minor: int,
) -> None:
    rounded = build_money_from_major_units(major_units, CurrencyCode(currency_code))

    assert rounded.amount_minor == expected_minor


@pytest.mark.parametrize(
    "major_units",
    [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity")],
)
def test_negative_and_non_finite_amounts_are_rejected(major_units: Decimal) -> None:
    with pytest.raises(ValidationFailedError):
        build_money_from_major_units(major_units, CurrencyCode("EUR"))


def test_conversion_uses_the_published_rate_exactly() -> None:
    rate = ExchangeRate(2.9552)

    assert convert_money(money(15, "EUR"), rate, CurrencyCode("GEL")) == money(
        44, "GEL"
    )
    assert convert_money(money(17500, "EUR"), rate, CurrencyCode("GEL")) == money(
        51716, "GEL"
    )
    assert convert_money(money(15000, "EUR"), rate, CurrencyCode("GEL")) == money(
        44328, "GEL"
    )
    # 0.1 + 0.2 style binary errors must not leak in: 1.15 EUR x 0.1 = 0.115.
    assert convert_money(
        money(115, "EUR"), ExchangeRate(0.1), CurrencyCode("USD")
    ) == money(12, "USD")
    assert convert_money(
        money(10000, "EUR"), ExchangeRate(161.5), CurrencyCode("JPY")
    ) == money(16150, "JPY")


def test_multiply_and_annual_discount() -> None:
    factor = Decimal(12) * build_discount_factor(DiscountPercent(15))

    assert build_discount_factor(DiscountPercent(15)) == Decimal("0.85")
    assert build_discount_factor(DiscountPercent(0)) == Decimal(1)
    assert multiply_money(money(17500, "EUR"), factor) == money(178500, "EUR")
    assert multiply_money(money(51700, "GEL"), factor) == money(527340, "GEL")
    assert multiply_money(money(1000, "JPY"), Decimal("0.333")) == money(333, "JPY")


@pytest.mark.parametrize(
    ("amount_minor", "currency_code", "language", "expected_text"),
    [
        (51700, "GEL", "ka", "517,00\xa0₾"),
        (51700, "GEL", "ru", "517,00\xa0GEL"),
        (51700, "GEL", "en", "GEL517.00"),
        (178500, "EUR", "ka", "1\xa0785,00\xa0€"),
        (178500, "EUR", "ru", "1\xa0785,00\xa0€"),
        (178500, "EUR", "en", "€1,785.00"),
        (178500, "EUR", "de", "1.785,00\xa0€"),
        (1234, "JPY", "en", "¥1,234"),
        (1234, "KWD", "en", "KWD1.234"),
        (9900, "USD", "en-US", "$99.00"),
        (9900, "BRL", "pt-BR", "R$\xa099,00"),
    ],
)
def test_formatting_follows_the_language(
    amount_minor: int,
    currency_code: str,
    language: str,
    expected_text: str,
) -> None:
    text = format_money(money(amount_minor, currency_code), LanguageTag(language))

    assert text == expected_text
    assert type(text) is FormattedMoneyText


@pytest.mark.parametrize("language", ["he", "ar", "fa"])
def test_right_to_left_formatting_keeps_latin_digits(language: str) -> None:
    text = format_money(money(51700, "GEL"), LanguageTag(language))

    assert "517" in text
    assert "00" in text


def test_formatting_in_an_unknown_language_is_rejected() -> None:
    with pytest.raises(UnsupportedLanguageError):
        format_money(money(100, "EUR"), LanguageTag("xx"))
