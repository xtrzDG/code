import pytest

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    TextDirection,
)
from app.schemas.dto.catalog import (
    CountryListRequest,
    CountryProfileRequest,
    ExchangeRateQuote,
    LanguageListRequest,
    ParsePhoneNumberRequest,
    PlanQuote,
    PlanQuoteRequest,
)
from app.schemas.exceptions.application_errors import (
    InvalidPhoneNumberError,
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
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.use_cases.catalog.get_country_profile_use_case import (
    GetCountryProfileUseCase,
)
from app.use_cases.catalog.list_countries_use_case import ListCountriesUseCase
from app.use_cases.catalog.list_languages_use_case import ListLanguagesUseCase
from app.use_cases.catalog.quote_plans_use_case import QuotePlansUseCase
from app.use_cases.localization.parse_phone_number_use_case import (
    ParsePhoneNumberUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from tests.localization.builders import (
    JULY_2026_NANOSECONDS,
    build_wall_clock,
    get_country_registry,
    get_language_registry,
)


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


def test_parse_phone_number_use_case_returns_e164() -> None:
    use_case = ParsePhoneNumberUseCase(phone_number_parser=PhoneNumberParser())

    details = use_case.run(
        ParsePhoneNumberRequest(
            raw_phone_number=RawPhoneNumberInput("8 (999) 123-45-67"),
            country_hint=CountryCode("RU"),
        )
    )

    assert details.e164 == "+79991234567"
    with pytest.raises(InvalidPhoneNumberError):
        use_case.run(
            ParsePhoneNumberRequest(raw_phone_number=RawPhoneNumberInput("12"))
        )


@pytest.mark.parametrize(
    ("language", "georgia_name", "israel_name"),
    [
        ("en", "Georgia", "Israel"),
        ("ru", "Грузия", "Израиль"),
        ("ka", "საქართველო", "ისრაელი"),
        ("he", "גאורגיה", "ישראל"),
        ("ar", "جورجيا", "إسرائيل"),
    ],
)
def test_countries_are_named_in_the_display_language(
    language: str,
    georgia_name: str,
    israel_name: str,
) -> None:
    use_case = ListCountriesUseCase(country_registry=get_country_registry())

    country_list = use_case.run(
        CountryListRequest(display_language=LanguageTag(language))
    )
    names_by_code = {
        str(country.country_code): str(country.display_name)
        for country in country_list.countries
    }

    assert len(country_list.countries) >= 200
    assert names_by_code["GE"] == georgia_name
    assert names_by_code["IL"] == israel_name
    display_names = [
        country.display_name.casefold() for country in country_list.countries
    ]
    assert display_names == sorted(display_names)


def test_country_list_keeps_restricted_countries_with_their_status() -> None:
    use_case = ListCountriesUseCase(country_registry=get_country_registry())

    countries = use_case.run(
        CountryListRequest(display_language=LanguageTag("en"))
    ).countries
    statuses = {
        str(country.country_code): country.onboarding_status for country in countries
    }

    assert statuses["IR"] is CountryOnboardingStatus.RESTRICTED
    assert statuses["GE"] is CountryOnboardingStatus.PILOT
    assert statuses["PL"] is CountryOnboardingStatus.SUPPORTED


def test_country_list_rejects_unknown_display_language() -> None:
    use_case = ListCountriesUseCase(country_registry=get_country_registry())

    with pytest.raises(UnsupportedLanguageError):
        use_case.run(CountryListRequest(display_language=LanguageTag("xx")))


def test_country_profile_view_renders_georgia_in_russian() -> None:
    use_case = GetCountryProfileUseCase(
        country_registry=get_country_registry(),
        language_registry=get_language_registry(),
        wall_clock=build_wall_clock(JULY_2026_NANOSECONDS),
    )

    view = use_case.run(
        CountryProfileRequest(
            country_code=CountryCode("GE"),
            display_language=LanguageTag("ru"),
        )
    )

    assert view.display_name == "Грузия"
    assert view.currency_display_name == "грузинский лари"
    assert view.default_timezone.display_name == "Asia/Tbilisi (UTC+04:00)"
    assert [str(option.display_name) for option in view.default_customer_languages] == [
        "грузинский",
        "русский",
        "английский",
    ]
    assert [str(option.native_name) for option in view.default_customer_languages] == [
        "ქართული",
        "русский",
        "English",
    ]
    on_request = {
        str(option.tag): option for option in view.on_request_customer_languages
    }
    assert on_request["he"].direction is TextDirection.RIGHT_TO_LEFT
    assert on_request["ar"].direction is TextDirection.RIGHT_TO_LEFT
    assert on_request["tr"].direction is TextDirection.LEFT_TO_RIGHT
    assert view.default_owner_language.tag == "ka"
    assert view.profile.emergency_number == "112"


def test_country_profile_view_shows_daylight_saving_offsets() -> None:
    use_case = GetCountryProfileUseCase(
        country_registry=get_country_registry(),
        language_registry=get_language_registry(),
        wall_clock=build_wall_clock(JULY_2026_NANOSECONDS),
    )

    view = use_case.run(
        CountryProfileRequest(
            country_code=CountryCode("US"),
            display_language=LanguageTag("es"),
        )
    )

    assert view.display_name == "Estados Unidos"
    assert view.default_timezone.display_name == "America/New_York (UTC-04:00)"
    assert len(view.timezones) == len(view.profile.timezones)


def test_country_profile_rejects_unknown_country() -> None:
    use_case = GetCountryProfileUseCase(
        country_registry=get_country_registry(),
        language_registry=get_language_registry(),
        wall_clock=build_wall_clock(),
    )

    with pytest.raises(UnknownCountryError):
        use_case.run(
            CountryProfileRequest(
                country_code=CountryCode("ZZ"),
                display_language=LanguageTag("en"),
            )
        )


def test_languages_are_listed_in_georgian_with_support_levels() -> None:
    use_case = ListLanguagesUseCase(language_registry=get_language_registry())

    language_list = use_case.run(
        LanguageListRequest(display_language=LanguageTag("ka"))
    )
    by_tag = {str(item.profile.tag): item for item in language_list.languages}

    assert by_tag["ka"].display_name == "ქართული"
    assert by_tag["ru"].display_name == "რუსული"
    assert by_tag["he"].profile.direction is TextDirection.RIGHT_TO_LEFT
    names = [item.display_name.casefold() for item in language_list.languages]
    assert names == sorted(names)


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
