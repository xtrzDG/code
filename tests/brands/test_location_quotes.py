"""
A plan quote priced for one location of a brand: a further location pays
the additional-location price (and its annual price follows), a location
whose brand's setup fee another one carries pays none, and a local price
that would not be billed is never shown.
"""

from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import PlanKey, SetupOption
from app.schemas.dto.catalog.plan_quotes import PlanQuote, PlanQuoteRequest
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.use_cases.catalog.quote_plans_use_case import QuotePlansUseCase
from app.utilities.brands.location_quotes import price_for_location
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.billing.exchange_rate_fixtures import rate_registry
from tests.localization.builders import get_country_registry

ENGLISH = LanguageTag("en")


def chat_quote(country: str) -> PlanQuote:
    quotes = QuotePlansUseCase(
        plan_registry=PlanRegistry(),
        country_registry=get_country_registry(),
        exchange_rate_registry=rate_registry(),
        localized_text_resolver=LocalizedTextResolver(),
    ).run(PlanQuoteRequest(country_code=CountryCode(country), display_language=ENGLISH))
    return next(quote for quote in quotes.quotes if quote.plan_key is PlanKey.CHAT)


def test_a_first_location_keeps_the_plan_price() -> None:
    quote = chat_quote("GE")

    assert price_for_location(quote, False, False, ENGLISH) == quote


def test_a_further_location_pays_the_additional_location_price() -> None:
    quote = chat_quote("GE")
    assert quote.local_additional_location_price is not None

    priced = price_for_location(quote, True, False, ENGLISH)

    assert priced.monthly_price == quote.additional_location_price
    assert priced.local_monthly_price == quote.local_additional_location_price
    assert priced.local_annual_price is not None
    discount = 1 - int(quote.annual_discount_percent) / 100
    monthly = int(quote.local_additional_location_price.money.amount_minor)
    assert int(priced.local_annual_price.money.amount_minor) == round(
        monthly * 12 * discount
    )
    assert priced.setup_fee == quote.setup_fee


def test_an_estimated_local_location_price_never_hides_a_price_book_plan_price() -> (
    None
):
    quote = chat_quote("GE")
    assert quote.local_additional_location_price is not None
    estimated = quote.local_additional_location_price.model_copy(
        update={"is_estimated": True}
    )
    without_book_price = quote.model_copy(
        update={"local_additional_location_price": estimated}
    )

    priced = price_for_location(without_book_price, True, False, ENGLISH)

    assert priced.local_monthly_price == quote.local_monthly_price


def test_a_covered_setup_fee_is_free_in_every_currency() -> None:
    quote = chat_quote("GE")

    priced = price_for_location(quote, True, True, ENGLISH)

    assert int(priced.setup_fee.money.amount_minor) == 0
    assert priced.local_setup_fee is not None
    assert int(priced.local_setup_fee.money.amount_minor) == 0
    done_for_you = next(
        option
        for option in priced.setup_options
        if option.option is SetupOption.DONE_FOR_YOU
    )
    assert int(done_for_you.fee.money.amount_minor) == 0
