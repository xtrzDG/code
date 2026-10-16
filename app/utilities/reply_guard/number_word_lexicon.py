"""
How numbers are written in words in one language, and the lexicon of a
conversation's languages together.

A lexicon lists the word forms of values ("fifty", "пятидесяти",
"ორმოცდაათ"), multipliers ("hundred", "тысяч", "אלפים"), joiners that glue
parts inside one word or between words ("-", "und", "და", the Hebrew and
Arabic "and" prefix), connector words between number words ("and", "y",
"et") and word endings a number may carry (Turkish "yedi-de", "at seven").
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

# Apostrophes of Ukrainian words ("п'ять", "пʼять", "п’ять"), the Russian
# "ё" and the Arabic alef forms are folded before a word is looked up.
APOSTROPHES: str = "'’ʼ`"
FOLDED_APOSTROPHE: str = "'"
FOLDED_LETTERS: dict[str, str] = {
    "ё": "е",
    "\u0623": "\u0627",
    "\u0625": "\u0627",
    "\u0622": "\u0627",
    "\u0671": "\u0627",
}


@dataclass(frozen=True, eq=False)
class NumberWordLexicon:
    """
    Number words of one or more languages (technical record).

    `values` are words with a value of their own (units, teens, tens and
    whole hundreds such as "двести" or "doscientos"); `multipliers` scale
    what comes before them ("hundred", "тысяч", "mil"); `teen_words` add
    ten to a unit before them (Hebrew "חמש עשרה", Arabic "خمسة عشر");
    `article_words` read as one only before a multiplier ("a hundred");
    `non_numbers` look like number words but are not (Turkish "yüzde",
    "percent", is not "yüz" + "de").
    `is_unit_before_tens` allows "five and twenty" (Arabic, German
    compounds); `is_tens_before_teens` allows "soixante et onze" (French).
    Lexicons compare by identity: the merged lexicon of a set of languages
    is built once and reused.
    """

    values: Mapping[str, int] = field(default_factory=dict[str, int])
    multipliers: Mapping[str, int] = field(default_factory=dict[str, int])
    joiners: frozenset[str] = frozenset()
    leading_prefixes: frozenset[str] = frozenset()
    connectors: frozenset[str] = frozenset()
    endings: frozenset[str] = frozenset()
    teen_words: frozenset[str] = frozenset()
    article_words: frozenset[str] = frozenset()
    non_numbers: frozenset[str] = frozenset()
    is_unit_before_tens: bool = False
    is_tens_before_teens: bool = False

    @property
    def morphemes(self) -> frozenset[str]:
        """Every form a word may be built from, longest first when segmenting."""

        return frozenset(self.values) | frozenset(self.multipliers) | self.joiners


def fold_word(word: str) -> str:
    """
    A word as lexicons spell it: lower case, one apostrophe, "е" for "ё",
    "ا" for every alef.
    """

    folded: str = word.lower()
    for apostrophe in APOSTROPHES:
        folded = folded.replace(apostrophe, FOLDED_APOSTROPHE)

    for letter, replacement in FOLDED_LETTERS.items():
        folded = folded.replace(letter, replacement)

    return folded


def with_stems(words: Mapping[str, int], ending: str) -> dict[str, int]:
    """The words and, for each one ending in `ending`, its form without it."""

    forms: dict[str, int] = dict(words)
    for word, value in words.items():
        if word.endswith(ending) and len(word) > len(ending) + 1:
            forms.setdefault(word[: -len(ending)], value)

    return forms


def merge_lexicons(lexicons: Iterable[NumberWordLexicon]) -> NumberWordLexicon:
    """
    The lexicon of several languages at once. A word two languages read
    differently keeps the value of the first language given.
    """

    values: dict[str, int] = {}
    multipliers: dict[str, int] = {}
    joiners: set[str] = set()
    prefixes: set[str] = set()
    connectors: set[str] = set()
    endings: set[str] = set()
    teen_words: set[str] = set()
    article_words: set[str] = set()
    non_numbers: set[str] = set()
    is_unit_before_tens: bool = False
    is_tens_before_teens: bool = False
    for lexicon in lexicons:
        for word, value in lexicon.values.items():
            values.setdefault(word, value)

        for word, value in lexicon.multipliers.items():
            multipliers.setdefault(word, value)

        joiners.update(lexicon.joiners)
        prefixes.update(lexicon.leading_prefixes)
        connectors.update(lexicon.connectors)
        endings.update(lexicon.endings)
        teen_words.update(lexicon.teen_words)
        article_words.update(lexicon.article_words)
        non_numbers.update(lexicon.non_numbers)
        is_unit_before_tens = is_unit_before_tens or lexicon.is_unit_before_tens
        is_tens_before_teens = is_tens_before_teens or lexicon.is_tens_before_teens

    return NumberWordLexicon(
        values=values,
        multipliers={
            word: value for word, value in multipliers.items() if word not in values
        },
        joiners=frozenset(joiners),
        leading_prefixes=frozenset(prefixes),
        connectors=frozenset(connectors),
        endings=frozenset(endings),
        teen_words=frozenset(teen_words),
        article_words=frozenset(article_words),
        non_numbers=frozenset(non_numbers),
        is_unit_before_tens=is_unit_before_tens,
        is_tens_before_teens=is_tens_before_teens,
    )
