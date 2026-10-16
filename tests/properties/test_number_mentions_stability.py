"""
Number mentions (the reply guard's reading of prices, times, dates and
phones) are stable: any text is read without an error, the same way every
time, into ordered, non-overlapping spans of the text itself; and what
follows a line break never changes what was read before it.
"""

from hypothesis import example, given
from hypothesis import strategies as st

from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.reply_guard.guard_lexicon import GuardLexicon, build_guard_lexicon
from app.utilities.reply_guard.number_mention import NumberMention
from app.utilities.reply_guard.number_mentions import extract_number_mentions

LEXICONS: dict[str, GuardLexicon] = {
    "ka": build_guard_lexicon(
        [LanguageTag("ka"), LanguageTag("en")], [CurrencyCode("GEL")]
    ),
    "ru": build_guard_lexicon(
        [LanguageTag("ru")], [CurrencyCode("RUB"), CurrencyCode("EUR")]
    ),
    "ar": build_guard_lexicon([LanguageTag("ar")], [CurrencyCode("AED")]),
}

# Digits of several numbering systems, separators, currency signs and words
# and month names: the material the patterns are made of.
PIECES: list[str] = [
    *"0123456789٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    *".,:/-+  %()₾€$₽",
    "GEL",
    "EUR",
    "лари",
    "руб",
    "ლარი",
    "AM",
    "PM",
    "ч",
    "мая",
    "იანვარი",
    "January",
    "сто",
    "двадцать",
    "ორი",
    "thirty",
    "+995 ",
    "8 (",
    "2026-",
    "T",
]

texts = st.lists(st.sampled_from(PIECES), max_size=40).map("".join) | st.text(
    max_size=60
)
languages = st.sampled_from(sorted(LEXICONS))


def spans(mentions: list[NumberMention]) -> list[tuple[int, int, str]]:
    return [(mention.start, mention.end, mention.text) for mention in mentions]


@given(texts, languages, st.booleans())
@example("Столик на 4 в 19:30, 25.10.2026, 120 лари, +995 555 12 34 56", "ru", False)
@example("ორი ადამიანი 20:00-ზე, 45,50 ₾", "ka", True)
def test_mentions_are_ordered_non_overlapping_spans_of_the_text(
    text: str, language: str, reads_words: bool
) -> None:
    mentions = extract_number_mentions(text, LEXICONS[language], reads_words)

    previous_end = 0
    for mention in mentions:
        assert previous_end <= mention.start < mention.end <= len(text)
        assert mention.text == text[mention.start : mention.end]
        previous_end = mention.end


@given(texts, languages, st.booleans())
def test_the_same_text_is_read_the_same_way_every_time(
    text: str, language: str, reads_words: bool
) -> None:
    first = extract_number_mentions(text, LEXICONS[language], reads_words)
    second = extract_number_mentions(text, LEXICONS[language], reads_words)

    assert first == second


@given(texts, texts, languages)
@example("Ждём вас в 19:30", "Цена 120 лари", "ru")
def test_a_following_line_does_not_change_what_was_read_before_it(
    text: str, following: str, language: str
) -> None:
    alone = extract_number_mentions(text, LEXICONS[language])
    joined = extract_number_mentions(f"{text}\n\n{following}", LEXICONS[language])

    before = [mention for mention in joined if mention.end <= len(text)]
    assert spans(before) == spans(alone)
    assert before == alone
