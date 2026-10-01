"""Names of countries, languages and currencies in any CLDR display language."""

from babel import Locale
from babel.numbers import get_currency_name

from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    CountryDisplayName,
    CurrencyDisplayName,
    LanguageDisplayName,
)
from app.utilities.localization.language_tags import (
    LanguageTagParts,
    get_english_locale,
    read_locale_name,
    split_language_tag,
)


def build_country_display_name(
    country_code: CountryCode,
    display_locale: Locale,
) -> CountryDisplayName:
    """Country name in the display locale, falling back to English, then the code."""

    name: str | None = read_locale_name(display_locale.territories, str(country_code))
    if name is None:
        name = read_locale_name(get_english_locale().territories, str(country_code))

    return CountryDisplayName(name if name is not None else str(country_code))


def build_currency_display_name(
    currency_code: CurrencyCode,
    display_locale: Locale,
) -> CurrencyDisplayName:
    """Currency name in the display locale, e.g. "ქართული ლარი" for GEL in ka."""

    return CurrencyDisplayName(
        get_currency_name(str(currency_code), locale=display_locale)
    )


def build_language_display_name(
    language_tag: LanguageTag,
    display_locale: Locale,
) -> LanguageDisplayName | None:
    """
    Language name in the display locale: "Portuguese (Brazil)", "中文 (繁體)".

    Returns None when the display locale has no name for the language.
    """

    parts: LanguageTagParts = split_language_tag(language_tag)
    language_name: str | None = read_locale_name(
        display_locale.languages,
        parts.language,
    )
    if language_name is None:
        return None

    details: list[str] = []
    if parts.script is not None:
        script_name: str | None = read_locale_name(display_locale.scripts, parts.script)
        details.append(script_name if script_name is not None else parts.script)

    if parts.region is not None:
        region_name: str | None = read_locale_name(
            display_locale.territories,
            parts.region,
        )
        details.append(region_name if region_name is not None else parts.region)

    if details == []:
        return LanguageDisplayName(language_name)

    return LanguageDisplayName(f"{language_name} ({', '.join(details)})")


def build_language_display_name_or_tag(
    language_tag: LanguageTag,
    display_locale: Locale,
) -> LanguageDisplayName:
    """Language name in the display locale, then in English, then the tag."""

    display_name: LanguageDisplayName | None = build_language_display_name(
        language_tag,
        display_locale,
    )
    if display_name is None:
        display_name = build_language_display_name(language_tag, get_english_locale())

    if display_name is None:
        return LanguageDisplayName(str(language_tag))

    return display_name
