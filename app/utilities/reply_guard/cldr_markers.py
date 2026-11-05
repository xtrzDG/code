"""
Words and symbols that turn a number into money or a date, from CLDR.

Currency symbols ("₾", "€", "US$", "zł", "֏", "₸", ...) of every CLDR
locale and ISO 4217 codes are recognized in any conversation. Currency
words ("лари", "шекелей", "dollars") come from the names of the business
currency in the conversation's languages, and month names ("октября",
"ოქტომბერი", "Oktober") from those languages only: across all languages
and currencies such words collide with ordinary words.
"""

import re
from collections.abc import Mapping
from decimal import Decimal
from functools import cache, lru_cache
from typing import Literal, cast

from babel import Locale, localedata
from babel.dates import get_month_names
from babel.numbers import get_currency_name, list_currencies

from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.babel_locales import find_babel_locale

WORD_PATTERN: re.Pattern[str] = re.compile(r"[^\W\d_]+")
MIN_CURRENCY_WORD_LENGTH: int = 3
MIN_ABBREVIATED_MONTH_LENGTH: int = 4
MONTH_NAME_FORMS: tuple[
    tuple[Literal["wide", "abbreviated"], Literal["format", "stand-alone"]], ...
] = (
    ("wide", "format"),
    ("wide", "stand-alone"),
    ("abbreviated", "format"),
    ("abbreviated", "stand-alone"),
)
# Words sharing this many first letters with a country or language name are
# adjectives of it ("georgian", "российский"), not currency words.
NAME_STEM_LENGTH: int = 5
MAX_CACHED_ENTRIES: int = 1024
# Counts that select every CLDR plural form (one, few, many, other, ...).
PLURAL_SAMPLE_COUNTS: tuple[int | Decimal, ...] = (1, 2, 5, 11, 21, 100, Decimal("1.5"))


@cache
def load_currency_codes() -> frozenset[str]:
    """ISO 4217 codes CLDR knows, upper case ("GEL", "EUR", "ILS")."""

    return frozenset(code.upper() for code in list_currencies())


@cache
def load_currency_symbols() -> frozenset[str]:
    """
    Symbols of every currency in every CLDR base locale, except single
    ASCII letters ("R", "K") that read as ordinary words.
    """

    symbols: set[str] = set()
    for locale_identifier in load_base_locale_identifiers():
        locale: Locale = Locale.parse(locale_identifier)
        for symbol in read_string_values(locale.currency_symbols):
            if not is_single_ascii_letter(symbol):
                symbols.add(symbol)

    return frozenset(symbols)


@lru_cache(maxsize=MAX_CACHED_ENTRIES)
def load_currency_words(language_code: str, currency_code: str) -> frozenset[str]:
    """
    Lower-case words of a currency's names in a language, in every plural
    form ("лари"; "шекель", "шекеля", "шекелей"; "dollar", "dollars"),
    without adjectives of countries and languages ("georgian", "ქართული").
    """

    locale: Locale | None = find_babel_locale(LanguageTag(language_code))
    if locale is None:
        return frozenset()

    excluded_words: set[str] = set()
    for name in read_string_values(locale.territories) + read_string_values(
        locale.languages
    ):
        excluded_words.update(WORD_PATTERN.findall(name.lower()))

    excluded_stems: set[str] = {
        word[:NAME_STEM_LENGTH]
        for word in excluded_words
        if len(word) >= NAME_STEM_LENGTH
    }
    names: set[str] = {
        get_currency_name(currency_code, count=count, locale=locale)
        for count in PLURAL_SAMPLE_COUNTS
    }
    currency_words: set[str] = set()
    for name in names:
        for word in WORD_PATTERN.findall(name.lower()):
            if (
                len(word) >= MIN_CURRENCY_WORD_LENGTH
                and word not in excluded_words
                and word[:NAME_STEM_LENGTH] not in excluded_stems
            ):
                currency_words.add(word)

    return frozenset(currency_words)


@lru_cache(maxsize=MAX_CACHED_ENTRIES)
def load_month_words(language_code: str) -> dict[str, frozenset[int]]:
    """
    Month names of a language in the format (genitive: "октября") and
    stand-alone ("октябрь") forms, and abbreviations of four letters or
    more ("sept", "janv"). Names written with digits ("10月") are skipped.
    """

    locale: Locale | None = find_babel_locale(LanguageTag(language_code))
    if locale is None:
        return {}

    months_by_word: dict[str, set[int]] = {}
    for width, context in MONTH_NAME_FORMS:
        names: Mapping[object, object] = cast(
            Mapping[object, object],
            get_month_names(width, context, locale),
        )
        for month_number, name in names.items():
            if not isinstance(month_number, int) or not isinstance(name, str):
                continue

            word: str = name.lower().rstrip(".")
            if any(character.isdigit() for character in word) or (
                width == "abbreviated" and len(word) < MIN_ABBREVIATED_MONTH_LENGTH
            ):
                continue

            months_by_word.setdefault(word, set()).add(month_number)

    return {word: frozenset(months) for word, months in months_by_word.items()}


@cache
def load_base_locale_identifiers() -> tuple[str, ...]:
    """CLDR locales without a region or script ("ka", "ru", "he", ...)."""

    return tuple(
        sorted(
            identifier
            for identifier in localedata.locale_identifiers()
            if "_" not in identifier
        )
    )


def read_string_values(mapping: object) -> list[str]:
    """String values of a Babel locale data mapping."""

    if not isinstance(mapping, Mapping):
        return []

    return [
        value
        for value in cast(Mapping[object, object], mapping).values()
        if isinstance(value, str) and value != ""
    ]


def is_single_ascii_letter(symbol: str) -> bool:
    return len(symbol) == 1 and symbol.isascii() and symbol.isalpha()
