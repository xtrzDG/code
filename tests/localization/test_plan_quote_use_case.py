"""
Plan quotes per country: the lari price book, euros, estimates and no invented dollars.
"""

import pytest

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import PlanKey
from app.schemas.dto.catalog.plan_quotes import (
    ExchangeRateQuote,
    PlanQuote,
    PlanQuoteRequest,
)
from app.schemas.exceptions.application_errors import (
    UnknownCountryError,
    UnsupportedLanguageError,
)
from app.schemas.typings.billing.constrained_floats import ExchangeRate
from app.schemas.typings.billing.constrained_strings import ExchangeRateDate
from app.schemas.typings.billing.strings import ExchangeRateSourceName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
)
from app.use_cases.catalog.quote_plans_use_case import QuotePlansUseCase
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.localization.builders import get_country_registry


def build_quote_plans_use_case(
    exchange_rate_registry: ExchangeRateRegistryContract | None = None,
) -> QuotePlansUseCase:
    return QuotePlansUseCase(
        plan_registry=PlanRegistry(),
        country_registry=get_country_registry(),
        exchange_rate_registry=(
            exchange_rate_registry
            if exchange_rate_registry is not None
            else ExchangeRateRegistry()
        ),
        localized_text_resolver=LocalizedTextResolver(),
    )


def find_quote(quotes: list[PlanQuote], plan_key: PlanKey) -> PlanQuote:
    return next(quote for quote in quotes if quote.plan_key is plan_key)


def test_georgian_quotes_come_from_the_lari_price_book() -> None:
    quote_list = build_quote_plans_use_case().run(
        PlanQuoteRequest(
            country_code=CountryCode("GE"), display_language=LanguageTag("ka")
        )
    )
    voice = find_quote(quote_list.quotes, PlanKey.VOICE_AND_CHAT)

    assert quote_list.local_currency_code == "GEL"
    assert voice.name == "ხმა + ჩატი"
    assert voice.monthly_price.money.amount_minor == 17500
    assert voice.monthly_price.text == "175,00\xa0€"
    assert voice.local_monthly_price is not None
    assert voice.local_monthly_price.money.amount_minor == 51700
    assert voice.local_monthly_price.text == "517,00\xa0₾"
    assert voice.local_monthly_price.is_estimated is False
    assert voice.local_setup_fee is not None
    assert voice.local_setup_fee.money.amount_minor == 44300
    assert voice.local_setup_fee.is_estimated is False
    assert voice.annual_price.money.amount_minor == 178500
    assert voice.local_annual_price is not None
    assert voice.local_annual_price.money.amount_minor == 527340
    assert voice.local_annual_price.is_estimated is False
    # The concept gives the overage only as "≈ 0.44 GEL": a conversion.
    assert voice.local_overage_price_per_minute is not None
    assert voice.local_overage_price_per_minute.money.amount_minor == 44
    assert voice.local_overage_price_per_minute.is_estimated is True
    assert quote_list.exchange_rate is not None
    assert quote_list.exchange_rate.rate == 2.9552
    chat = find_quote(quote_list.quotes, PlanKey.CHAT)
    plus = find_quote(quote_list.quotes, PlanKey.PLUS)
    assert chat.local_monthly_price is not None
    assert chat.local_monthly_price.money.amount_minor == 29300
    assert plus.local_monthly_price is not None
    assert plus.local_monthly_price.money.amount_minor == 103100


@pytest.mark.parametrize(
    ("language", "expected_name", "expected_monthly_text"),
    [
        ("ru", "Голос + чат", "175,00\xa0€"),
        ("en", "Voice + chat", "€175.00"),
        ("de", "Voice + chat", "175,00\xa0€"),
    ],
)
def test_quotes_are_rendered_in_the_display_language(
    language: str,
    expected_name: str,
    expected_monthly_text: str,
) -> None:
    quote_list = build_quote_plans_use_case().run(
        PlanQuoteRequest(
            country_code=CountryCode("GE"), display_language=LanguageTag(language)
        )
    )
    voice = find_quote(quote_list.quotes, PlanKey.VOICE_AND_CHAT)

    assert voice.name == expected_name
    assert voice.monthly_price.text == expected_monthly_text


def test_usa_quotes_never_invent_a_dollar_price() -> None:
    quote_list = build_quote_plans_use_case().run(
        PlanQuoteRequest(
            country_code=CountryCode("US"), display_language=LanguageTag("en")
        )
    )

    assert quote_list.local_currency_code == "USD"
    assert quote_list.exchange_rate is None
    for quote in quote_list.quotes:
        assert quote.monthly_price.money.currency_code == "EUR"
        assert quote.local_monthly_price is None
        assert quote.local_annual_price is None
        assert quote.local_setup_fee is None
        assert quote.local_overage_price_per_minute is None


def test_euro_countries_get_the_euro_price_as_local() -> None:
    quote_list = build_quote_plans_use_case().run(
        PlanQuoteRequest(
            country_code=CountryCode("LT"), display_language=LanguageTag("lt")
        )
    )
    plus = find_quote(quote_list.quotes, PlanKey.PLUS)

    assert quote_list.exchange_rate is None
    assert plus.local_monthly_price is not None
    assert plus.local_monthly_price.money == plus.monthly_price.money
    assert plus.local_monthly_price.is_estimated is False
    assert plus.local_overage_price_per_minute is not None
    assert plus.local_overage_price_per_minute.money.amount_minor == 15


def test_a_known_rate_gives_estimated_local_prices() -> None:
    armenian_rate = ExchangeRateQuote(
        base_currency_code=CurrencyCode("EUR"),
        quote_currency_code=CurrencyCode("AMD"),
        rate=ExchangeRate(450.0),
        rate_date=ExchangeRateDate("2026-09-30"),
        source=ExchangeRateSourceName("Test central bank"),
    )
    quote_list = build_quote_plans_use_case(
        ExchangeRateRegistry(exchange_rates=(armenian_rate,))
    ).run(
        PlanQuoteRequest(
            country_code=CountryCode("AM"), display_language=LanguageTag("hy")
        )
    )
    chat = find_quote(quote_list.quotes, PlanKey.CHAT)

    assert quote_list.exchange_rate == armenian_rate
    assert chat.local_monthly_price is not None
    assert chat.local_monthly_price.money.amount_minor == 4455000
    assert chat.local_monthly_price.money.currency_code == "AMD"
    assert chat.local_monthly_price.is_estimated is True
    assert chat.local_annual_price is not None
    assert chat.local_annual_price.is_estimated is True
    assert chat.local_setup_fee is not None
    assert chat.local_setup_fee.is_estimated is True


def test_quotes_reject_unknown_countries_and_languages() -> None:
    use_case = build_quote_plans_use_case()

    with pytest.raises(UnknownCountryError):
        use_case.run(
            PlanQuoteRequest(
                country_code=CountryCode("ZZ"), display_language=LanguageTag("en")
            )
        )
    with pytest.raises(UnsupportedLanguageError):
        use_case.run(
            PlanQuoteRequest(
                country_code=CountryCode("GE"), display_language=LanguageTag("xx")
            )
        )
