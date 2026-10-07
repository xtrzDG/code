"""
The markers that classify numbers in one conversation: currencies, months
and number words.

Currency symbols and ISO 4217 codes are recognized in any conversation;
currency words (with the case forms of Georgian and Turkish: "ლარად",
"liraya"), month names and number words only in the conversation's
languages and English (see `cldr_markers` and `numerals.NUMBER_WORDS`).
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.localization.language_tags import base_language_code
from app.utilities.reply_guard.cldr_markers import (
    load_currency_codes,
    load_currency_symbols,
    load_currency_words,
    load_month_words,
)
from app.utilities.reply_guard.number_word_lexicon import NumberWordLexicon
from app.utilities.reply_guard.numerals import number_words_for

# Inflected month names keep the name without its last letter.
MIN_MONTH_STEM_LENGTH: int = 4
ENGLISH_LANGUAGE_CODE: str = "en"
# Case forms of currency words: the final letter a form drops, then its
# endings ("ლარი" -> "ლარად", "lira" -> "liraya").
CURRENCY_WORD_ENDINGS: dict[str, tuple[str, tuple[str, ...]]] = {
    "ka": ("ი", ("ს", "ის", "ად", "ით", "ზე", "ამდე", "იდან", "ში")),
    "tr": ("", ("ya", "ye", "yı", "yi", "dan", "den", "da", "de", "lık", "lik")),
}


@dataclass(frozen=True)
class GuardLexicon:
    """Markers used to classify numbers in one conversation (technical record)."""

    currency_symbols: frozenset[str]
    currency_codes: frozenset[str]
    currency_words: frozenset[str]
    month_words: Mapping[str, frozenset[int]]
    month_stems: Mapping[str, frozenset[int]]
    number_words: NumberWordLexicon

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
            words: frozenset[str] = load_currency_words(language_code, currency_code)
            currency_words.update(words)
            currency_words.update(inflect_currency_words(language_code, words))

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
        number_words=number_words_for(sorted(language_codes)),
    )


def inflect_currency_words(language_code: str, words: Iterable[str]) -> set[str]:
    """Case forms of currency words in a language that inflects them."""

    rule: tuple[str, tuple[str, ...]] | None = CURRENCY_WORD_ENDINGS.get(language_code)
    if rule is None:
        return set()

    dropped, endings = rule
    forms: set[str] = set()
    for word in words:
        stem: str = word.removesuffix(dropped) if dropped else word
        forms.update(f"{stem}{ending}" for ending in endings)

    return forms
