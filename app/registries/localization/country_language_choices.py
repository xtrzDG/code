"""Which languages a country's profile offers: official, customer, on request.

Curated tables win; otherwise the choice is derived from CLDR territory
data and the languages the assistant supports.
"""

from app.contracts.registries import LanguageRegistryContract
from app.registries.localization.curated_country_languages import (
    CURATED_CUSTOMER_LANGUAGES,
    CURATED_ON_REQUEST_LANGUAGES,
    CURATED_OWNER_LANGUAGES,
    MAX_DERIVED_OFFICIAL_LANGUAGES,
    MAX_DERIVED_ON_REQUEST_LANGUAGES,
    MIN_ON_REQUEST_POPULATION_PERCENT,
    TOURIST_LANGUAGE,
)
from app.registries.localization.territory_languages import TerritoryLanguage
from app.schemas.constants.localization import LanguageTextSupport
from app.schemas.dto.localization import LanguageProfile
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.utilities.localization.language_tags import (
    base_language_code,
    find_babel_locale,
)


def find_owner_language(
    country_code: CountryCode,
    official_languages: list[LanguageTag],
    customer_languages: list[LanguageTag],
) -> LanguageTag:
    curated_language: LanguageTag | None = CURATED_OWNER_LANGUAGES.get(country_code)
    if curated_language is not None:
        return curated_language

    if official_languages != []:
        return official_languages[0]

    return customer_languages[0] if customer_languages != [] else TOURIST_LANGUAGE


def has_language(language_tags: list[LanguageTag], language_tag: LanguageTag) -> bool:
    """True when a tag with the same language subtag is already in the list."""

    language_code: str = base_language_code(language_tag)
    return any(
        base_language_code(listed_tag) == language_code for listed_tag in language_tags
    )


def append_new_language(
    language_tags: list[LanguageTag],
    language_tag: LanguageTag,
) -> list[LanguageTag]:
    if has_language(language_tags, language_tag):
        return language_tags

    return [*language_tags, language_tag]


def find_official_languages(
    language_registry: LanguageRegistryContract,
    territory_languages: list[TerritoryLanguage],
) -> list[LanguageTag]:
    """Official languages with CLDR locale data, one per language subtag."""

    official_languages: list[LanguageTag] = []
    for territory_language in territory_languages:
        if not territory_language.is_official:
            continue

        if (
            find_language_profile(language_registry, territory_language.language_tag)
            is None
        ):
            continue

        if find_babel_locale(territory_language.language_tag) is None:
            continue

        official_languages = append_new_language(
            official_languages,
            territory_language.language_tag,
        )

    return official_languages


def find_customer_languages(
    country_code: CountryCode,
    official_languages: list[LanguageTag],
) -> list[LanguageTag]:
    curated_languages: tuple[LanguageTag, ...] | None = CURATED_CUSTOMER_LANGUAGES.get(
        country_code
    )
    if curated_languages is not None:
        return list(curated_languages)

    customer_languages: list[LanguageTag] = official_languages[
        :MAX_DERIVED_OFFICIAL_LANGUAGES
    ]
    return append_new_language(customer_languages, TOURIST_LANGUAGE)


def find_on_request_languages(
    language_registry: LanguageRegistryContract,
    country_code: CountryCode,
    territory_languages: list[TerritoryLanguage],
    customer_languages: list[LanguageTag],
) -> list[LanguageTag]:
    """Large resident languages the assistant writes well, not yet default."""

    curated_languages: tuple[LanguageTag, ...] | None = (
        CURATED_ON_REQUEST_LANGUAGES.get(country_code)
    )
    if curated_languages is not None:
        return list(curated_languages)

    on_request_languages: list[LanguageTag] = []
    for territory_language in territory_languages:
        if len(on_request_languages) >= MAX_DERIVED_ON_REQUEST_LANGUAGES:
            break

        if (
            territory_language.is_official
            or territory_language.population_percent < MIN_ON_REQUEST_POPULATION_PERCENT
        ):
            continue

        profile: LanguageProfile | None = find_language_profile(
            language_registry, territory_language.language_tag
        )
        if profile is None or profile.text_support is not (
            LanguageTextSupport.SUPPORTED
        ):
            continue

        if has_language(customer_languages, profile.tag):
            continue

        on_request_languages = append_new_language(
            on_request_languages,
            profile.tag,
        )

    return on_request_languages


def find_language_profile(
    language_registry: LanguageRegistryContract,
    language_tag: LanguageTag,
) -> LanguageProfile | None:
    try:
        return language_registry.get(language_tag)
    except UnsupportedLanguageError:
        return None
