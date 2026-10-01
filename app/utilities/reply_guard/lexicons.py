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
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from functools import cache, lru_cache
from typing import Literal, cast

from babel import Locale, localedata
from babel.dates import get_month_names
from babel.numbers import get_currency_name, list_currencies

from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.localization.language_tags import (
    base_language_code,
    find_babel_locale,
)

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
# Inflected month names keep the name without its last letter.
MIN_MONTH_STEM_LENGTH: int = 4
# Words sharing this many first letters with a country or language name are
# adjectives of it ("georgian", "российский"), not currency words.
NAME_STEM_LENGTH: int = 5
ENGLISH_LANGUAGE_CODE: str = "en"
MAX_CACHED_ENTRIES: int = 1024
# Counts that select every CLDR plural form (one, few, many, other, ...).
PLURAL_SAMPLE_COUNTS: tuple[int | Decimal, ...] = (1, 2, 5, 11, 21, 100, Decimal("1.5"))
# Words around a bare number that make it a clock hour ("at 7", "в 7",
# "um 7 Uhr", "7-ზე", "à 7 heures"). CLDR has no prepositions, so this is a
# short curated list; words that also introduce counts ("на", "до", "a")
# are left out on purpose.
HOUR_PREFIX_WORDS: frozenset[str] = frozenset(
    {
        "@",
        "after",
        "alle",
        "around",
        "at",
        "before",
        "bis",
        "dalle",
        "desde",
        "dès",
        "gegen",
        "hacia",
        "hasta",
        "las",
        "till",
        "um",
        "until",
        "vers",
        "verso",
        "à",
        "às",
        "в",
        "во",
        "к",
        "ко",
        "около",
        "после",
        "сағат",
        "ժամը",
        "בשעה",
        "الساعة",
        "saat",
    }
)
HOUR_SUFFIX_WORDS: frozenset[str] = frozenset(
    {
        "h",
        "heure",
        "heures",
        "hora",
        "horas",
        "o'clock",
        "o’clock",
        "ora",
        "ore",
        "uhr",
        "вечера",
        "дня",
        "ночи",
        "утра",
        "час",
        "часа",
        "часов",
        "ժամին",
        "ზე",
        "საათზე",
        "საათისთვის",
    }
)


@dataclass(frozen=True)
class GuardLexicon:
    """Markers used to classify numbers in one conversation (technical record)."""

    currency_symbols: frozenset[str]
    currency_codes: frozenset[str]
    currency_words: frozenset[str]
    month_words: Mapping[str, frozenset[int]]
    month_stems: Mapping[str, frozenset[int]]

    def is_currency_marker(self, token: str) -> bool:
        return (
            token in self.currency_symbols
            or token in self.currency_codes
            or token.lower() in self.currency_words
        )

    def find_months(self, word: str) -> frozenset[int]:
        """
        Months a word names, also in an inflected form at most one letter
        longer than the name ("ოქტომბერს" for "ოქტომბერი", "октябре" for
        "октябрь", "հոկտեմբերին" for "հոկտեմբերի").
        """

        lowered_word: str = word.lower().rstrip(".")
        exact_months: frozenset[int] | None = self.month_words.get(lowered_word)
        if exact_months is not None:
            return exact_months

        for stem_length in range(len(lowered_word) - 1, MIN_MONTH_STEM_LENGTH - 1, -1):
            if len(lowered_word) > stem_length + 2:
                break

            stem_months: frozenset[int] | None = self.month_stems.get(
                lowered_word[:stem_length]
            )
            if stem_months is not None:
                return stem_months

        return frozenset()


def build_guard_lexicon(
    language_tags: Iterable[LanguageTag],
    currency_codes: Iterable[CurrencyCode],
) -> GuardLexicon:
    """
    Lexicon for the given languages plus English (the platform language) and
    the given currencies (the business currency).
    """

    language_codes: set[str] = {ENGLISH_LANGUAGE_CODE}
    language_codes.update(base_language_code(tag) for tag in language_tags)
    currency_words: set[str] = set()
    month_words: dict[str, frozenset[int]] = {}
    for language_code in sorted(language_codes):
        for currency_code in sorted({str(code) for code in currency_codes}):
            currency_words.update(load_currency_words(language_code, currency_code))

        for word, months in load_month_words(language_code).items():
            month_words[word] = month_words.get(word, frozenset()) | months

    month_stems: dict[str, frozenset[int]] = {}
    for word, months in month_words.items():
        if len(word) > MIN_MONTH_STEM_LENGTH:
            stem: str = word[:-1]
            month_stems[stem] = month_stems.get(stem, frozenset()) | months

    return GuardLexicon(
        currency_symbols=load_currency_symbols(),
        currency_codes=load_currency_codes(),
        currency_words=frozenset(currency_words),
        month_words=month_words,
        month_stems=month_stems,
    )


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
