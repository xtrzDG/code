"""Checks shared by business creation and settings changes.

Values are checked, never rewritten: a valid input is used as it came in.
"""

import zoneinfo
from functools import cache

from app.contracts.registries import LanguageRegistryContract
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)

MAX_BUSINESS_NAME_LENGTH: int = 200
MAX_CITY_NAME_LENGTH: int = 120
MIN_BUSINESS_LANGUAGES: int = 1
MAX_BUSINESS_LANGUAGES: int = 10
# Entries of the IANA database that are links to the host setting or
# placeholders, not real places.
NON_GEOGRAPHIC_TIMEZONE_NAMES: frozenset[str] = frozenset(
    {"Factory", "localtime", "posixrules"}
)


def require_valid_business_name(name: BusinessName) -> None:
    """Raise ValidationFailedError for a blank or overlong name."""

    if name.strip() == "":
        raise ValidationFailedError("Business name must not be empty.")

    if len(name) > MAX_BUSINESS_NAME_LENGTH:
        raise ValidationFailedError(
            f"Business name must be at most {MAX_BUSINESS_NAME_LENGTH} characters."
        )


def require_valid_city_name(city: CityName) -> None:
    """Raise ValidationFailedError for an overlong city name."""

    if len(city) > MAX_CITY_NAME_LENGTH:
        raise ValidationFailedError(
            f"City must be at most {MAX_CITY_NAME_LENGTH} characters."
        )


def require_existing_timezone(timezone: TimezoneName) -> None:
    """Raise ValidationFailedError unless the IANA database knows the zone."""

    if timezone not in list_geographic_timezone_names():
        raise ValidationFailedError(f"Unknown time zone {str(timezone)!r}.")


@cache
def list_geographic_timezone_names() -> frozenset[str]:
    return frozenset(zoneinfo.available_timezones() - NON_GEOGRAPHIC_TIMEZONE_NAMES)


def validate_business_languages(
    languages: list[LanguageTag],
    language_registry: LanguageRegistryContract,
) -> list[LanguageTag]:
    """
    Return the languages without repeats, in the given order.

    Raises:
        UnsupportedLanguageError: a tag unknown to the language registry.
        ValidationFailedError: fewer than 1 or more than 10 languages.
    """

    unique_languages: list[LanguageTag] = []
    for language in languages:
        language_registry.get(language)
        if language not in unique_languages:
            unique_languages.append(language)

    if not MIN_BUSINESS_LANGUAGES <= len(unique_languages) <= MAX_BUSINESS_LANGUAGES:
        raise ValidationFailedError(
            f"A business needs {MIN_BUSINESS_LANGUAGES} to "
            f"{MAX_BUSINESS_LANGUAGES} customer languages."
        )

    return unique_languages
