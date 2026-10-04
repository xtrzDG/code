"""
Numbers written in words, read next to the words that give them a
meaning: a currency ("fifty lari", "ორმოცდაათი ლარი", "две тысячи лари"),
a percentage ("twenty percent", "yüzde yirmi") or a clock hour ("at
nine.", "um sieben Uhr", "saat yedide", "الساعة السابعة").

In a reply only such numbers are checked: "two guests" or "one of our
branches" invent nothing. In the evidence every number word counts, so a
fact that says "parking for fifty cars" backs "50" in a reply.
"""

from app.utilities.reply_guard.guard_lexicon import GuardLexicon
from app.utilities.reply_guard.hour_words import HOUR_PREFIX_WORDS
from app.utilities.reply_guard.number_mention import LocalTime, NumberMention
from app.utilities.reply_guard.number_patterns import HOURS_PER_DAY, NOON
from app.utilities.reply_guard.number_word_context import (
    ARABIC_HOUR_ORDINALS,
    ARABIC_HOUR_WORD,
    CLAUSE_END_MARKS,
    NUMBER_WORD_HOUR_SUFFIXES,
    PERCENT_PHRASES,
    PERCENT_PREFIX_WORDS,
    PERCENT_WORDS,
    STRONG_HOUR_PREFIX_WORDS,
    WEAK_HOUR_PREFIX_WORDS,
)
from app.utilities.reply_guard.number_word_lexicon import fold_word
from app.utilities.reply_guard.number_word_sequences import (
    NumberRun,
    TextToken,
    find_number_runs,
    tokenize,
)
from app.utilities.reply_guard.plain_number_mentions import is_currency_token


def extract_number_word_mentions(
    text: str,
    normalized_text: str,
    lexicon: GuardLexicon,
    reads_plain_numbers: bool = False,
) -> list[NumberMention]:
    """
    Numbers written in words (or digits scaled by a word: "2 тысячи"),
    as money, percentages and clock hours; with `reads_plain_numbers`
    (evidence) also every other one, as a plain number.
    """

    tokens: list[TextToken] = tokenize(normalized_text)
    mentions: list[NumberMention] = [
        mention
        for mention in (
            read_run_mention(text, tokens, run, lexicon, reads_plain_numbers)
            for run in find_number_runs(tokens, lexicon.number_words)
        )
        if mention is not None
    ]
    mentions.extend(read_arabic_hours(text, tokens))
    return mentions


def read_run_mention(
    text: str,
    tokens: list[TextToken],
    run: NumberRun,
    lexicon: GuardLexicon,
    reads_plain_numbers: bool,
) -> NumberMention | None:
    first: TextToken = tokens[run.first]
    last: TextToken = tokens[run.last]
    after: TextToken | None = token_at(tokens, run.last + 1)
    before: TextToken | None = token_at(tokens, run.first - 1)
    if after is not None and is_currency_token(after.text, lexicon):
        return build_mention(text, first.start, after.end, run, is_money=True)

    if before is not None and is_currency_prefix_token(before, tokens, run, lexicon):
        return build_mention(text, before.start, last.end, run, is_money=True)

    percent_end: int | None = find_percent_end(tokens, run.last + 1)
    if percent_end is not None:
        return build_mention(text, first.start, percent_end, run, is_percent=True)

    if before is not None and before.folded in PERCENT_PREFIX_WORDS:
        return build_mention(text, before.start, last.end, run, is_percent=True)

    times: frozenset[LocalTime] = read_hour(tokens, run)
    if times:
        is_suffixed: bool = (
            after is not None and after.folded in NUMBER_WORD_HOUR_SUFFIXES
        )
        start: int = (
            before.start
            if before is not None and before.folded in HOUR_PREFIX_WORDS
            else first.start
        )
        end: int = after.end if after is not None and is_suffixed else last.end
        return NumberMention(text=text[start:end], start=start, end=end, times=times)

    if not reads_plain_numbers:
        return None

    return build_mention(text, first.start, last.end, run)


def build_mention(
    text: str,
    start: int,
    end: int,
    run: NumberRun,
    is_money: bool = False,
    is_percent: bool = False,
) -> NumberMention:
    return NumberMention(
        text=text[start:end],
        start=start,
        end=end,
        is_money=is_money,
        is_percent=is_percent,
        amounts=frozenset({run.value}),
    )


def token_at(tokens: list[TextToken], index: int) -> TextToken | None:
    return tokens[index] if 0 <= index < len(tokens) else None


def is_currency_prefix_token(
    before: TextToken,
    tokens: list[TextToken],
    run: NumberRun,
    lexicon: GuardLexicon,
) -> bool:
    """A currency symbol or code right before the number ("$ fifty")."""

    if before.is_word and before.text.lower() == before.text:
        # Lower-case words before a number are currency words only after
        # it ("fifty lari"); "lari fifty" is not how anyone writes money.
        return False

    earlier: TextToken | None = token_at(tokens, run.first - 2)
    if earlier is not None and earlier.is_number:
        return False

    return lexicon.is_currency_marker(before.text)


def find_percent_end(tokens: list[TextToken], index: int) -> int | None:
    """The end of a percent word or phrase starting at `index`."""

    word: TextToken | None = token_at(tokens, index)
    if word is None:
        return None

    if word.folded in PERCENT_WORDS:
        return word.end

    second: TextToken | None = token_at(tokens, index + 1)
    if second is not None and (word.folded, second.folded) in PERCENT_PHRASES:
        return second.end

    return None


def read_hour(tokens: list[TextToken], run: NumberRun) -> frozenset[LocalTime]:
    """
    The clock times a number may be when an hour word frames it: a strong
    hour word before it ("saat", "um", "a las"), an hour word after it
    ("o'clock", "часов", "საათზე"), or a preposition before it ("at", "в")
    when the clause ends right after the number.
    """

    if (
        run.value != run.value.to_integral_value()
        or not 0 <= run.value <= HOURS_PER_DAY
    ):
        return frozenset()

    before: TextToken | None = token_at(tokens, run.first - 1)
    after: TextToken | None = token_at(tokens, run.last + 1)
    before_word: str = "" if before is None else before.folded
    after_word: str = "" if after is None else after.folded
    is_hour: bool = (
        before_word in STRONG_HOUR_PREFIX_WORDS
        or after_word in NUMBER_WORD_HOUR_SUFFIXES
        or (
            before_word in WEAK_HOUR_PREFIX_WORDS
            and (after is None or after.text in CLAUSE_END_MARKS)
        )
    )
    if not is_hour:
        return frozenset()

    return clock_readings(int(run.value))


def clock_readings(hour: int) -> frozenset[LocalTime]:
    """An hour said without "am" or "pm": the morning and the evening one."""

    readings: set[LocalTime] = {(hour % HOURS_PER_DAY, 0)}
    if 1 <= hour < NOON:
        readings.add((hour + NOON, 0))

    return frozenset(readings)


def read_arabic_hours(text: str, tokens: list[TextToken]) -> list[NumberMention]:
    """Arabic hours said as ordinals: "الساعة السابعة" (at seven)."""

    mentions: list[NumberMention] = []
    for index, token in enumerate(tokens[:-1]):
        if token.folded != fold_word(ARABIC_HOUR_WORD):
            continue

        hour_word: TextToken = tokens[index + 1]
        hour: int | None = ARABIC_HOUR_ORDINALS.get(hour_word.folded)
        if hour is None:
            continue

        mentions.append(
            NumberMention(
                text=text[token.start : hour_word.end],
                start=token.start,
                end=hour_word.end,
                times=clock_readings(hour),
            )
        )

    return mentions
