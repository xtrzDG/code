import pytest

from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import BillingPeriod, PlanKey
from app.schemas.dto.billing import Money
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.use_cases.billing.subscription_pricing import (
    price_overage_per_minute,
    price_setup_fee,
    price_subscription,
    quote_money,
    select_subscription_currency,
)
from tests.billing.billing_testbed import PriceBookPlanRegistry


def money(amount_minor: int, currency_code: str) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(amount_minor),
        currency_code=CurrencyCode(currency_code),
    )


@pytest.mark.parametrize(
    ("business_currency", "expected"),
    [("GEL", "GEL"), ("EUR", "EUR"), ("USD", "EUR"), ("JPY", "EUR"), ("ILS", "EUR")],
)
def test_subscription_currency_follows_the_price_book(
    business_currency: str,
    expected: str,
) -> None:
    assert select_subscription_currency(
        PlanRegistry(),
        PlanKey.VOICE_AND_CHAT,
        CurrencyCode(business_currency),
    ) == CurrencyCode(expected)


def test_a_currency_needs_both_price_and_setup_fee_in_the_price_book() -> None:
    registry = PriceBookPlanRegistry(
        monthly_prices={(PlanKey.CHAT, "JPY"): 16000},
    )

    assert select_subscription_currency(
        registry, PlanKey.CHAT, CurrencyCode("JPY")
    ) == CurrencyCode("EUR")


@pytest.mark.parametrize(
    ("plan_key", "currency", "billing_period", "expected"),
    [
        (PlanKey.CHAT, "GEL", BillingPeriod.MONTHLY, 29300),
        (PlanKey.VOICE_AND_CHAT, "GEL", BillingPeriod.MONTHLY, 51700),
        (PlanKey.VOICE_AND_CHAT, "GEL", BillingPeriod.ANNUAL, 527340),
        (PlanKey.PLUS, "GEL", BillingPeriod.ANNUAL, 1051620),
        (PlanKey.CHAT, "EUR", BillingPeriod.ANNUAL, 100980),
        (PlanKey.VOICE_AND_CHAT, "EUR", BillingPeriod.ANNUAL, 178500),
    ],
)
def test_annual_price_is_twelve_months_minus_fifteen_percent(
    plan_key: PlanKey,
    currency: str,
    billing_period: BillingPeriod,
    expected: int,
) -> None:
    assert price_subscription(
        PlanRegistry(),
        plan_key,
        billing_period,
        CurrencyCode(currency),
    ) == money(expected, currency)


@pytest.mark.parametrize(
    ("currency", "monthly", "annual"),
    [
        ("GEL", 33333, 339997),
        ("EUR", 9999, 101990),
        ("JPY", 1333, 13597),
        ("JPY", 1332, 13586),
        ("KWD", 33333, 339997),
    ],
)
def test_annual_price_is_rounded_half_up_in_minor_units(
    currency: str,
    monthly: int,
    annual: int,
) -> None:
    registry = PriceBookPlanRegistry(
        monthly_prices={(PlanKey.CHAT, currency): monthly},
    )

    assert price_subscription(
        registry,
        PlanKey.CHAT,
        BillingPeriod.ANNUAL,
        CurrencyCode(currency),
    ) == money(annual, currency)


def test_prices_are_never_converted() -> None:
    with pytest.raises(ValidationFailedError):
        price_subscription(
            PlanRegistry(),
            PlanKey.CHAT,
            BillingPeriod.MONTHLY,
            CurrencyCode("USD"),
        )

    with pytest.raises(ValidationFailedError):
        price_setup_fee(PlanRegistry(), PlanKey.CHAT, CurrencyCode("USD"))


def test_setup_fee_comes_from_the_price_book() -> None:
    assert price_setup_fee(PlanRegistry(), PlanKey.PLUS, CurrencyCode("GEL")) == (
        money(44300, "GEL")
    )
    assert price_setup_fee(PlanRegistry(), PlanKey.PLUS, CurrencyCode("EUR")) == (
        money(15000, "EUR")
    )


def test_overage_price_is_estimated_only_with_an_official_rate() -> None:
    plan = PlanRegistry().get(PlanKey.VOICE_AND_CHAT)
    rates = ExchangeRateRegistry()

    assert price_overage_per_minute(plan, CurrencyCode("GEL"), rates) == (
        money(44, "GEL"),
        True,
    )
    assert price_overage_per_minute(plan, CurrencyCode("EUR"), rates) == (
        money(15, "EUR"),
        False,
    )
    assert price_overage_per_minute(plan, CurrencyCode("JPY"), rates) == (
        money(15, "EUR"),
        False,
    )


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("ka", "517,00\xa0₾"),
        ("ru", "517,00\xa0GEL"),
        ("en", "GEL517.00"),
        ("he", "\u200f517.00\xa0\u200fGEL"),
    ],
)
def test_money_is_quoted_in_the_reader_language(language: str, expected: str) -> None:
    quoted = quote_money(money(51700, "GEL"), False, LanguageTag(language))

    assert quoted.text == expected
    assert not quoted.is_estimated
