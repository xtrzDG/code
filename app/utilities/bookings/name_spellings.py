"""
Latin spellings of names written in any script, so "ნინო", "Нино" and
"נינו" all find the master "Nino".

Georgian, Cyrillic and Armenian letters follow the public chat addresses'
tables (`slug_transliteration`); Greek, Hebrew and Arabic letters are
added here. Hebrew and Arabic are written mostly without vowels, so their
names are also compared by consonants (`consonant_skeleton`). Letters of
other scripts stay as they are: a Japanese name still matches itself.
"""

import unicodedata
from collections.abc import Mapping

from app.utilities.knowledge.search_text import WORD_PATTERN, fold_text
from app.utilities.sharing.slug_transliteration import LETTER_SPELLINGS

GREEK_LETTERS: Mapping[str, str] = {
    "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i",
    "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "x",
    "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y",
    "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o",
}  # fmt: skip

# Hebrew letters as consonants (alef and ayin are silent); vav and yod also
# write vowels, which `consonant_skeleton` drops.
HEBREW_LETTERS: Mapping[str, str] = {
    "א": "", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "v", "ז": "z",
    "ח": "kh", "ט": "t", "י": "y", "כ": "k", "ך": "k", "ל": "l", "מ": "m",
    "ם": "m", "נ": "n", "ן": "n", "ס": "s", "ע": "", "פ": "p", "ף": "f",
    "צ": "ts", "ץ": "ts", "ק": "k", "ר": "r", "ש": "sh", "ת": "t",
}  # fmt: skip

ARABIC_LETTERS: Mapping[str, str] = {
    "ا": "a", "أ": "a", "إ": "i", "آ": "a", "ب": "b", "ت": "t", "ث": "th",
    "ج": "j", "ح": "h", "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z",
    "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "",
    "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n",
    "ه": "h", "ة": "a", "و": "w", "ي": "y", "ى": "a", "ء": "", "پ": "p",
    "چ": "ch", "ژ": "zh", "گ": "g", "ک": "k", "ی": "y",
}  # fmt: skip

NAME_LETTER_SPELLINGS: Mapping[str, str] = {
    **LETTER_SPELLINGS,
    **GREEK_LETTERS,
    **HEBREW_LETTERS,
    **ARABIC_LETTERS,
}
# Letters that write vowels (or nothing) once a name is spelled in Latin.
VOWEL_LETTERS: frozenset[str] = frozenset("aeiouyvwh")
# Hebrew and Arabic code points (their own and presentation forms).
ABJAD_RANGES: tuple[tuple[int, int], ...] = (
    (0x0590, 0x05FF),
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0xFB1D, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def spell_name_in_latin(text: str) -> str:
    """
    The words of a name in Latin letters, folded and separated by single
    spaces ("Нино Беридзе" gives "nino beridze"; "ნინო" gives "nino").
    """

    spelled: list[str] = []
    for character in fold_text(text):
        mapped: str | None = NAME_LETTER_SPELLINGS.get(character)
        if mapped is not None:
            spelled.append(mapped)
            continue

        decomposed: str = unicodedata.normalize("NFKD", character)
        latin: str = "".join(
            part for part in decomposed if part.isascii() and part.isalnum()
        )
        spelled.append(latin.lower() if latin else character)

    return " ".join(WORD_PATTERN.findall("".join(spelled)))


def consonant_skeleton(latin_words: str) -> str:
    """The consonants of Latin-spelled words, without spaces ("nino" -> "nn")."""

    return "".join(
        character
        for character in latin_words
        if character.isalnum() and character not in VOWEL_LETTERS
    )


def is_abjad_text(text: str) -> bool:
    """Whether the text has Hebrew or Arabic letters (names written without vowels)."""

    return any(
        start <= ord(character) <= end
        for character in text
        for start, end in ABJAD_RANGES
    )
