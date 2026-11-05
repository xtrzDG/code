"""Language-neutral text folding and tokenization for lexical search.

Works without external models for any script:

- Unicode NFKC, case folding and removal of combining marks fold accents,
  Hebrew niqqud and Arabic harakat ("Café" = "cafe", "й" = "и").
- Script-specific spellings are unified: Hebrew final letters, Arabic and
  Persian alef/yeh/kaf/teh marbuta variants, Arabic tatweel.
- Scripts written without spaces (Chinese, Japanese, Korean, Thai, Lao,
  Khmer, Myanmar) are split into character unigrams and bigrams, because
  their words cannot be found by spaces.
"""

import re
import unicodedata
from dataclasses import dataclass

WORD_PATTERN: re.Pattern[str] = re.compile(r"[^\W_]+")

# Code point ranges of scripts written without spaces between words.
NO_SPACE_SCRIPT_RANGES: tuple[tuple[int, int], ...] = (
    (0x0E00, 0x0EFF),  # Thai, Lao
    (0x1000, 0x109F),  # Myanmar
    (0x1780, 0x17FF),  # Khmer
    (0x3040, 0x30FF),  # Hiragana, Katakana
    (0x31F0, 0x31FF),  # Katakana phonetic extensions
    (0x3400, 0x4DBF),  # CJK extension A
    (0x4E00, 0x9FFF),  # CJK unified ideographs
    (0xAC00, 0xD7AF),  # Hangul syllables
    (0xF900, 0xFAFF),  # CJK compatibility ideographs
    (0x20000, 0x2FA1F),  # CJK extensions B and later
)

SCRIPT_FOLDS: dict[int, str] = str.maketrans(
    {
        # Hebrew final letters -> regular forms.
        "ך": "כ",
        "ם": "מ",
        "ן": "נ",
        "ף": "פ",
        "ץ": "צ",
        # Arabic and Persian spelling variants.
        "ى": "ي",
        "ی": "ي",
        "ک": "ك",
        "ة": "ه",
        "ـ": "",
    }
)

# Scripts whose words carry attached prefix particles (Hebrew ה/ו/ב/ל,
# Arabic ال/و/ب): "הפיצה" is "the pizza", "الفلافل" is "the falafel".
PREFIXED_PARTICLE_SCRIPT_RANGES: tuple[tuple[int, int], ...] = (
    (0x0590, 0x05FF),  # Hebrew
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic supplement
    (0xFB1D, 0xFDFF),  # Hebrew and Arabic presentation forms
    (0xFE70, 0xFEFF),  # Arabic presentation forms B
)

UNIGRAM_WEIGHT: float = 0.5
BIGRAM_WEIGHT: float = 1.0
WORD_WEIGHT: float = 1.0


@dataclass(frozen=True)
class SearchToken:
    """
    One folded token with its weight in scoring.

    `allows_partial` is False for character n-grams of scripts without spaces:
    they match only exactly, never by prefix or edit distance.
    """

    text: str
    weight: float
    allows_partial: bool


def fold_text(text: str) -> str:
    """Fold case, accents and script spelling variants for comparison."""

    composed: str = unicodedata.normalize("NFKC", text).casefold()
    decomposed: str = unicodedata.normalize("NFD", composed)
    without_marks: str = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return unicodedata.normalize("NFC", without_marks).translate(SCRIPT_FOLDS)


def fold_words(text: str) -> str:
    """Folded words of a text joined by single spaces (punctuation dropped)."""

    return " ".join(WORD_PATTERN.findall(fold_text(text)))


def contains_phrase(text: str, phrase: str) -> bool:
    """
    Whether folded `phrase` occurs in folded `text` as whole words.

    Space-less scripts have no word boundaries, so there any occurrence counts.
    """

    if phrase == "":
        return False

    if any(is_space_less_character(character) for character in phrase):
        return phrase in text

    return f" {phrase} " in f" {text} "


def tokenize(text: str) -> list[SearchToken]:
    """Split text into folded word tokens and n-grams of space-less scripts."""

    tokens: list[SearchToken] = []
    for word in WORD_PATTERN.findall(fold_text(text)):
        tokens.extend(split_word(word))

    return tokens


def split_word(word: str) -> list[SearchToken]:
    """Split one folded word into spaced-script parts and space-less n-grams."""

    tokens: list[SearchToken] = []
    run: list[str] = []
    is_run_space_less: bool = False
    for character in word:
        is_space_less: bool = is_space_less_character(character)
        if run != [] and is_space_less != is_run_space_less:
            tokens.extend(tokens_of_run("".join(run), is_run_space_less))
            run = []

        run.append(character)
        is_run_space_less = is_space_less

    if run != []:
        tokens.extend(tokens_of_run("".join(run), is_run_space_less))

    return tokens


def tokens_of_run(run: str, is_space_less: bool) -> list[SearchToken]:
    if not is_space_less:
        return [SearchToken(text=run, weight=WORD_WEIGHT, allows_partial=True)]

    if len(run) == 1:
        return [SearchToken(text=run, weight=BIGRAM_WEIGHT, allows_partial=False)]

    unigrams: list[SearchToken] = [
        SearchToken(text=character, weight=UNIGRAM_WEIGHT, allows_partial=False)
        for character in run
    ]
    bigrams: list[SearchToken] = [
        SearchToken(
            text=run[index : index + 2],
            weight=BIGRAM_WEIGHT,
            allows_partial=False,
        )
        for index in range(len(run) - 1)
    ]
    return unigrams + bigrams


def is_space_less_character(character: str) -> bool:
    code_point: int = ord(character)
    return any(start <= code_point <= end for start, end in NO_SPACE_SCRIPT_RANGES)


def has_prefixed_particles(word: str) -> bool:
    """Whether a word is written in a script with attached prefix particles."""

    return word != "" and any(
        start <= ord(word[0]) <= end for start, end in PREFIXED_PARTICLE_SCRIPT_RANGES
    )


def unique_tokens(tokens: list[SearchToken]) -> list[SearchToken]:
    """Drop repeated tokens, keeping the first (and therefore its weight)."""

    seen_texts: set[str] = set()
    unique: list[SearchToken] = []
    for token in tokens:
        if token.text in seen_texts:
            continue

        seen_texts.add(token.text)
        unique.append(token)

    return unique
