"""
Reading one written word as a number: "fifty" is 50, "fünfundzwanzig"
25, "ორმოცდაათ" 50, "وعشرين" 20, "yedide" 7, "quatre-vingt-dix" 90.

A word is split into lexicon parts that cover all of it (an "and" prefix,
values, multipliers and joiners, a case ending last); the split with the
fewest parts wins, so "quatre-vingt" reads as eighty, not four and twenty.
The parts of one word add up, multipliers scaling what came before them
("zweihundert" is 2 x 100).
"""

from dataclasses import dataclass
from functools import lru_cache

from app.utilities.reply_guard.number_word_lexicon import NumberWordLexicon

MAX_PREFIXES: int = 2
MAX_CACHED_WORDS: int = 4096
HUNDRED: int = 100
THOUSAND: int = 1000


@dataclass(frozen=True)
class WordNumber:
    """
    The number one word writes (technical record): its value, whether it
    is a bare multiplier ("thousand", "тысяч"), and whether a prefix was
    attached to it (the Arabic "and" of "وعشرون").
    """

    value: int
    is_multiplier: bool = False
    is_prefixed: bool = False


def read_word_number(word: str, lexicon: NumberWordLexicon) -> WordNumber | None:
    """The number a folded word writes, or None when it is no number."""

    return _read_cached(word, lexicon)


@lru_cache(maxsize=MAX_CACHED_WORDS)
def _read_cached(word: str, lexicon: NumberWordLexicon) -> WordNumber | None:
    if word in lexicon.non_numbers:
        return None

    if word in lexicon.multipliers:
        return WordNumber(value=lexicon.multipliers[word], is_multiplier=True)

    if word in lexicon.values:
        return WordNumber(value=lexicon.values[word])

    for prefix_length, stem in strip_prefixes(word, lexicon):
        parts: list[str] | None = split_into_parts(stem, lexicon)
        if parts is None:
            continue

        value: int | None = add_parts(parts, lexicon)
        if value is None:
            continue

        is_multiplier: bool = len(parts) == 1 and parts[0] in lexicon.multipliers
        return WordNumber(
            value=value,
            is_multiplier=is_multiplier,
            is_prefixed=prefix_length > 0,
        )

    return None


def strip_prefixes(word: str, lexicon: NumberWordLexicon) -> list[tuple[int, str]]:
    """The word without up to two attached prefixes, the bare word first."""

    stems: list[tuple[int, str]] = [(0, word)]
    frontier: list[str] = [word]
    for _ in range(MAX_PREFIXES):
        next_frontier: list[str] = []
        for stem in frontier:
            for prefix in lexicon.leading_prefixes:
                if stem.startswith(prefix) and len(stem) > len(prefix):
                    shorter: str = stem[len(prefix) :]
                    stems.append((len(word) - len(shorter), shorter))
                    next_frontier.append(shorter)

        frontier = next_frontier

    return stems


def split_into_parts(word: str, lexicon: NumberWordLexicon) -> list[str] | None:
    """
    The fewest lexicon parts that spell the whole word, with at most one
    case ending at its end; None when no split covers it.
    """

    morphemes: frozenset[str] = lexicon.morphemes
    best: list[list[str] | None] = [None] * (len(word) + 1)
    best[0] = []
    for end in range(1, len(word) + 1):
        for start in range(end):
            before: list[str] | None = best[start]
            piece: str = word[start:end]
            if before is None or piece not in morphemes:
                continue

            candidate: list[str] = [*before, piece]
            current: list[str] | None = best[end]
            if current is None or len(candidate) < len(current):
                best[end] = candidate

    whole: list[str] | None = best[len(word)]
    if whole is not None:
        return whole

    for ending in lexicon.endings:
        if word.endswith(ending) and len(word) > len(ending):
            stem_parts: list[str] | None = best[len(word) - len(ending)]
            if stem_parts:
                return stem_parts

    return None


def add_parts(parts: list[str], lexicon: NumberWordLexicon) -> int | None:
    """
    The value of the parts of one word; None when it has only joiners or
    starts with one.
    """

    total: int = 0
    current: int = 0
    has_value: bool = False
    for index, part in enumerate(parts):
        if part in lexicon.joiners:
            if index == 0:
                return None
            continue

        has_value = True
        if part in lexicon.multipliers:
            multiplier: int = lexicon.multipliers[part]
            if multiplier >= THOUSAND:
                total += max(current, 1) * multiplier
                current = 0
            else:
                current = max(current, 1) * multiplier
            continue

        current += lexicon.values[part]

    if not has_value or parts[-1] in lexicon.joiners:
        return None

    return total + current
