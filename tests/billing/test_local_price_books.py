"""
The local price books: every priced currency has every plan's monthly
price, setup fee and further-location price, each a rounded whole amount
set by hand, and every country paying in such a currency is billed in it.
"""

import pytest

from app.registries.billing.local_price_books import (
    MINOR_UNITS_PER_MAJOR,
    PRICE_TABLE,
)
from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import BillingPeriod, PlanKey, SetupOption
from app.schemas.dto.billing import Money
from app.schemas.dto.localization import CountryProfile
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.shared.subscription_pricing import (
    price_setup_fee,
    price_subscription,
    select_subscription_currency,
)
from app.utilities.money.money_math import get_currency_minor_unit_digits
from tests.localization.builders import get_country_registry

PLANS = PlanRegistry()
PRICED_CURRENCIES: list[str] = sorted(str(code) for code in PRICE_TABLE)
REGIONAL_CURRENCIES: list[str] = ["AMD", "ILS", "KZT", "PLN", "USD"]


def test_the_books_price_the_regional_currencies_and_lari() -> None:
    assert PRICED_CURRENCIES == ["AMD", "GEL", "ILS", "KZT", "PLN", "USD"]


@pytest.mark.parametrize("currency", PRICED_CURRENCIES)
@pytest.mark.parametrize("plan_key", list(PlanKey))
def test_every_priced_currency_has_every_plan_price(
    currency: str, plan_key: PlanKey
) -> None:
    code = CurrencyCode(currency)

    monthly = PLANS.find_local_monthly_price(plan_key, code)
    setup_fee = PLANS.find_local_setup_fee(plan_key, code)
    location = PLANS.find_local_additional_location_price(plan_key, code)

    assert monthly is not None and monthly.currency_code == code
    assert setup_fee is not None and setup_fee.currency_code == code
    assert location is not None and location.currency_code == code
    # A further location of a brand always costs less than the first.
    assert int(location.amount_minor) < int(monthly.amount_minor)


@pytest.mark.parametrize("currency", PRICED_CURRENCIES)
def test_the_books_have_two_minor_digits_like_their_currencies(currency: str) -> None:
    assert 10 ** int(get_currency_minor_unit_digits(CurrencyCode(currency))) == (
        MINOR_UNITS_PER_MAJOR
    )


@pytest.mark.parametrize("currency", REGIONAL_CURRENCIES)
def test_regional_prices_are_rounded_whole_amounts(currency: str) -> None:
    for prices in PRICE_TABLE[CurrencyCode(currency)].values():
        for whole_units in prices:
            assert whole_units > 0
            assert whole_units % 10 == 9 or whole_units % 100 == 0, whole_units


@pytest.mark.parametrize("currency", PRICED_CURRENCIES)
def test_bigger_plans_cost_more_in_every_book(currency: str) -> None:
    code = CurrencyCode(currency)
    monthly: list[int] = []
    for plan_key in (PlanKey.CHAT, PlanKey.VOICE_AND_CHAT, PlanKey.PLUS):
        price: Money | None = PLANS.find_local_monthly_price(plan_key, code)
        assert price is not None
        monthly.append(int(price.amount_minor))

    assert monthly == sorted(monthly) and len(set(monthly)) == 3


def priced_countries() -> list[CountryProfile]:
    priced: set[CurrencyCode] = set(PRICE_TABLE)
    return [
        country
        for country in get_country_registry().list_all()
        if country.currency_code in priced
    ]


def test_every_priced_country_is_billed_in_its_own_currency() -> None:
    countries = priced_countries()

    assert {"AM", "GE", "IL", "KZ", "PL", "US"} <= {
        str(country.country_code) for country in countries
    }
    for country in countries:
        for plan_key in PlanKey:
            currency = select_subscription_currency(
                PLANS, plan_key, country.currency_code
            )
            assert currency == country.currency_code, country.country_code
            assert price_subscription(
                PLANS, plan_key, BillingPeriod.MONTHLY, currency
            ).currency_code == (currency)
            assert price_setup_fee(PLANS, plan_key, currency).currency_code == currency
            free = PLANS.find_setup_fee(plan_key, SetupOption.SELF_SERVE, currency)
            assert free is not None and int(free.amount_minor) == 0
