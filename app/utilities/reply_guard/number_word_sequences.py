"""
Numbers written as a run of words ("one hundred and fifty", "две тысячи",
"ორას ორმოცდაათი", "خمسة وعشرون") or as digits scaled by a word ("2
тысячи", "1,5 million"), with where they stand in the text.

Words join one number only in a valid order: "fifty five" is 55, but
"ten fifty" is two numbers, so a word that happens to be a number in
another language ("on" is ten in Turkish) does not glue onto a real one.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from app.utilities.reply_guard.number_word_lexicon import NumberWordLexicon, fold_word
from app.utilities.reply_guard.number_word_parsing import (
    HUNDRED,
    THOUSAND,
    WordNumber,
    read_word_number,
)
from app.utilities.reply_guard.numerals import parse_amount_candidates

TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"(?P<word>[^\W\d_]+(?:[-'’ʼ.][^\W\d_]+)*)"
    r"|(?P<number>\d+(?:[.,]\d+)?)"
    r"|(?P<mark>\S)"
)
TENS: int = 10
TEENS_END: int = 20


@dataclass(frozen=True)
class TextToken:
    """One word, number or mark of a text with its place (technical record)."""

    text: str
    folded: str
    start: int
    end: int
    is_word: bool
    is_number: bool


@dataclass(frozen=True)
class NumberRun:
    """
    A number written in words or scaled by a word (technical record):
    tokens `first` to `last` (inclusive) of the text.
    """

    first: int
    last: int
    value: Decimal


@dataclass
class RunState:
    """The number read so far: finished thousands and the open group."""

    total: int = 0
    group: int = 0


def tokenize(text: str) -> list[TextToken]:
    """Words, numbers and single marks, in order (digits normalized first)."""

    tokens: list[TextToken] = []
    for match in TOKEN_PATTERN.finditer(text):
        token_text: str = match.group(0)
        is_word: bool = match.group("word") is not None
        tokens.append(
            TextToken(
                text=token_text,
                folded=fold_word(token_text) if is_word else token_text,
                start=match.start(),
                end=match.end(),
                is_word=is_word,
                is_number=match.group("number") is not None,
            )
        )

    return tokens


def find_number_runs(
    tokens: list[TextToken], lexicon: NumberWordLexicon
) -> list[NumberRun]:
    """Every number written in words, or in digits scaled by a word."""

    runs: list[NumberRun] = []
    index: int = 0
    while index < len(tokens):
        run: NumberRun | None = read_run(tokens, index, lexicon)
        if run is None:
            index += 1
            continue

        runs.append(run)
        index = run.last + 1

    return runs


def read_run(
    tokens: list[TextToken], first: int, lexicon: NumberWordLexicon
) -> NumberRun | None:
    token: TextToken = tokens[first]
    if token.is_number:
        return read_scaled_digits(tokens, first, lexicon)

    if not token.is_word:
        return None

    state = RunState()
    last: int = first
    start_number: WordNumber | None = read_word_number(token.folded, lexicon)
    if start_number is None:
        if token.folded not in lexicon.article_words:
            return None
        multiplier: WordNumber | None = word_number_at(tokens, first + 1, lexicon)
        if multiplier is None or not multiplier.is_multiplier:
            return None
        start_number = WordNumber(value=1)

    if not extend(state, start_number, token.folded, lexicon, is_joined=False):
        return None

    index: int = first + 1
    while index < len(tokens):
        is_joined: bool = False
        candidate_index: int = index
        if tokens[index].folded in lexicon.connectors:
            is_joined = True
            candidate_index = index + 1

        number: WordNumber | None = word_number_at(tokens, candidate_index, lexicon)
        if number is None:
            break

        joined: bool = is_joined or number.is_prefixed
        folded: str = tokens[candidate_index].folded
        if not extend(state, number, folded, lexicon, is_joined=joined):
            break

        last = candidate_index
        index = candidate_index + 1

    return NumberRun(first=first, last=last, value=Decimal(state.total + state.group))


def read_scaled_digits(
    tokens: list[TextToken], first: int, lexicon: NumberWordLexicon
) -> NumberRun | None:
    """Digits followed by a multiplier word ("2 тысячи", "1,5 million")."""

    multiplier: WordNumber | None = word_number_at(tokens, first + 1, lexicon)
    if multiplier is None or not multiplier.is_multiplier:
        return None

    amounts: frozenset[Decimal] = parse_amount_candidates(tokens[first].text)
    if len(amounts) != 1:
        return None

    (amount,) = amounts
    return NumberRun(first=first, last=first + 1, value=amount * multiplier.value)


def word_number_at(
    tokens: list[TextToken], index: int, lexicon: NumberWordLexicon
) -> WordNumber | None:
    if index >= len(tokens) or not tokens[index].is_word:
        return None

    return read_word_number(tokens[index].folded, lexicon)


def extend(
    state: RunState,
    number: WordNumber,
    folded: str,
    lexicon: NumberWordLexicon,
    is_joined: bool,
) -> bool:
    """Add one word to the number when it may follow what came before."""

    value: int = number.value
    if number.is_multiplier:
        return scale(state, value)

    rest: int = state.group % HUNDRED
    if folded in lexicon.teen_words and 1 <= rest < TENS:
        state.group += TENS
        return True

    if value >= THOUSAND:
        if state.total or state.group:
            return False
        state.total = value
        return True

    if value >= HUNDRED:
        if state.group:
            return False
        state.group = value
        return True

    if value >= TENS:
        if not may_add_tens(rest, value, lexicon, is_joined):
            return False
        state.group += value
        return True

    if rest % TENS != 0 or TENS <= rest < TEENS_END:
        return False

    state.group += value
    return True


def may_add_tens(
    rest: int, value: int, lexicon: NumberWordLexicon, is_joined: bool
) -> bool:
    """Tens or a teen after what the open group holds below a hundred."""

    if rest == 0:
        return True

    is_teen: bool = value < TEENS_END
    if lexicon.is_tens_before_teens and is_teen and rest % TENS == 0:
        return rest >= TEENS_END and rest + value < HUNDRED

    return (
        lexicon.is_unit_before_tens
        and is_joined
        and not is_teen
        and value % TENS == 0
        and 1 <= rest < TENS
    )


def scale(state: RunState, multiplier: int) -> bool:
    """A multiplier word: hundreds scale the group, thousands close it."""

    if multiplier < THOUSAND:
        if state.group >= HUNDRED:
            return False
        state.group = max(state.group, 1) * multiplier
        return True

    if state.total and state.total % (multiplier * THOUSAND) != 0:
        return False

    state.total += max(state.group, 1) * multiplier
    state.group = 0
    return True
