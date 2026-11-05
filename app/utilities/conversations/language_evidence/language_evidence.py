"""How a language looks in writing: the record and helpers to write it down."""

from typing import NamedTuple


class LanguageEvidence(NamedTuple):
    """
    How a language looks in writing (a technical lookup record).

    `script` is the ISO 15924 code the evidence is written in (a language
    may also be written in another script, like "sr-Latn"). `alphabet`
    lists every letter of that script the language uses; letters of the
    script outside it count against the language. None means the alphabet
    is not checked.
    """

    script: str
    alphabet: frozenset[str] | None
    distinctive_letters: frozenset[str]
    frequent_words: frozenset[str]


def words(text: str) -> frozenset[str]:
    return frozenset(text.split())


def letters(text: str) -> frozenset[str]:
    return frozenset(text)
