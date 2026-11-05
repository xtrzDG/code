"""Catalog use cases: phone parsing, country lists and profiles, language lists."""

import pytest

from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.localization import CountryOnboardingStatus, TextDirection
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.catalog.countries import (
    CountryListRequest,
    CountryProfileRequest,
    LanguageListRequest,
    ParsePhoneNumberRequest,
)
from app.schemas.exceptions.application_errors import (
    InvalidPhoneNumberError,
    UnknownCountryError,
    UnsupportedLanguageError,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.use_cases.catalog.get_country_profile_use_case import GetCountryProfileUseCase
from app.use_cases.catalog.list_countries_use_case import ListCountriesUseCase
from app.use_cases.catalog.list_languages_use_case import ListLanguagesUseCase
from app.use_cases.localization.parse_phone_number_use_case import (
    ParsePhoneNumberUseCase,
)
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from tests.localization.builders import (
    JULY_2026_NANOSECONDS,
    build_wall_clock,
    get_country_registry,
    get_language_registry,
)


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
    use_case = ListCountriesUseCase(
        country_registry=get_country_registry(), plan_registry=PlanRegistry()
    )

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
    use_case = ListCountriesUseCase(
        country_registry=get_country_registry(), plan_registry=PlanRegistry()
    )

    countries = use_case.run(
        CountryListRequest(display_language=LanguageTag("en"))
    ).countries
    statuses = {
        str(country.country_code): country.onboarding_status for country in countries
    }

    assert statuses["IR"] is CountryOnboardingStatus.RESTRICTED
    assert statuses["IT"] is CountryOnboardingStatus.PILOT
    assert statuses["GE"] is CountryOnboardingStatus.SUPPORTED
    assert statuses["PL"] is CountryOnboardingStatus.SUPPORTED


def test_country_list_rejects_unknown_display_language() -> None:
    use_case = ListCountriesUseCase(
        country_registry=get_country_registry(), plan_registry=PlanRegistry()
    )

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


def test_country_list_says_which_countries_have_explicit_prices() -> None:
    use_case = ListCountriesUseCase(
        country_registry=get_country_registry(), plan_registry=PlanRegistry()
    )

    countries = use_case.run(
        CountryListRequest(display_language=LanguageTag("en"))
    ).countries
    price_books = {
        str(country.country_code): country.has_price_book for country in countries
    }

    # The local price books and the plans' own euros; yen are conversions.
    assert price_books["GE"] is True
    assert price_books["DE"] is True
    assert price_books["US"] is True
    assert price_books["AM"] is True
    assert price_books["IL"] is True
    assert price_books["KZ"] is True
    assert price_books["PL"] is True
    assert price_books["JP"] is False
    assert price_books["RU"] is False


class CountingPlanRegistry(PlanRegistry):
    """The plan registry, counting the plans it hands out."""

    def __init__(self) -> None:
        super().__init__()
        self.lists: int = 0
        self.gets: int = 0

    def get(self, plan_key: PlanKey) -> PlanDefinition:
        self.gets += 1
        return super().get(plan_key)

    def list_all(self) -> list[PlanDefinition]:
        self.lists += 1
        return super().list_all()


def test_country_list_works_out_each_currency_once() -> None:
    plans = CountingPlanRegistry()
    use_case = ListCountriesUseCase(
        country_registry=get_country_registry(), plan_registry=plans
    )

    countries = use_case.run(
        CountryListRequest(display_language=LanguageTag("en"))
    ).countries

    # One list of plans per request and at most one plan copied per currency:
    # asking the registry per country copied plans 1898 times (a third of a
    # second of every landing page's render).
    assert plans.lists == 1
    assert plans.gets <= len({country.currency_code for country in countries})
