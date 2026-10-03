"""
Catalog of countries and languages, and phone number parsing, for
businesses in any country.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.localization import CountryOnboardingStatus, TextDirection
from app.schemas.dto.localization import CountryProfile, LanguageProfile
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import (
    CountryDisplayName,
    CurrencyDisplayName,
    LanguageDisplayName,
    RawPhoneNumberInput,
    TimezoneDisplayName,
)


class ParsePhoneNumberRequest(ImmutableDTO):
    """
    A phone number as typed, with the country to read national formats in.

    Example: {"raw_phone_number": "8 (999) 123-45-67", "country_hint": "RU"}.
    """

    raw_phone_number: RawPhoneNumberInput
    country_hint: CountryCode | None = None


class CountryListRequest(ImmutableDTO):
    """Every country with names in the display language."""

    display_language: LanguageTag


class CountryListItem(ImmutableDTO):
    """Summary of one country for a country picker."""

    country_code: CountryCode
    display_name: CountryDisplayName
    english_name: CountryDisplayName
    calling_code: CountryCallingCode
    currency_code: CurrencyCode
    default_timezone: TimezoneName
    default_owner_language: LanguageTag
    onboarding_status: CountryOnboardingStatus


class CountryList(ImmutableDTO):
    """Countries ordered by their name in the display language."""

    display_language: LanguageTag
    countries: list[CountryListItem]


class CountryProfileRequest(ImmutableDTO):
    """One country's defaults, described in the display language."""

    country_code: CountryCode
    display_language: LanguageTag


class LanguageOption(ImmutableDTO):
    """A language as a picker shows it: in the display language and natively."""

    tag: LanguageTag
    display_name: LanguageDisplayName
    native_name: LanguageDisplayName
    direction: TextDirection


class TimezoneOption(ImmutableDTO):
    """An IANA time zone with its current UTC offset."""

    name: TimezoneName
    display_name: TimezoneDisplayName


class CountryProfileView(ImmutableDTO):
    """A country profile with every code rendered for people."""

    profile: CountryProfile
    display_language: LanguageTag
    display_name: CountryDisplayName
    currency_display_name: CurrencyDisplayName
    timezones: list[TimezoneOption]
    default_timezone: TimezoneOption
    default_customer_languages: list[LanguageOption]
    on_request_customer_languages: list[LanguageOption]
    default_owner_language: LanguageOption


class LanguageListRequest(ImmutableDTO):
    """Every listed language with names in the display language."""

    display_language: LanguageTag


class LanguageListItem(ImmutableDTO):
    """A language profile with its name in the display language."""

    profile: LanguageProfile
    display_name: LanguageDisplayName


class LanguageList(ImmutableDTO):
    """Languages ordered by their name in the display language."""

    display_language: LanguageTag
    languages: list[LanguageListItem]
