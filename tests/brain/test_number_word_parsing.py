"""Reading single number words and runs of them, language by language."""

import pytest

from app.utilities.reply_guard.number_word_lexicon import (
    NumberWordLexicon,
    fold_word,
    merge_lexicons,
)
from app.utilities.reply_guard.number_word_parsing import (
    WordNumber,
    add_parts,
    read_word_number,
)
from app.utilities.reply_guard.number_word_sequences import find_number_runs, tokenize
from app.utilities.reply_guard.numerals import NUMBER_WORDS, number_words_for
from tests.brain.reply_guard_helpers import mentions


@pytest.mark.parametrize(
    ("word", "language", "expected"),
    [
        ("fifty", "en", WordNumber(50)),
        ("thousand", "en", WordNumber(1000, is_multiplier=True)),
        ("fünfundzwanzig", "de", WordNumber(25)),
        ("zweihundert", "de", WordNumber(200)),
        ("ორმოცდაათ", "ka", WordNumber(50)),
        ("შვიდზე", "ka", WordNumber(7)),
        ("yedide", "tr", WordNumber(7)),
        ("وعشرون", "ar", WordNumber(20, is_prefixed=True)),
        ("ובחמישים", "he", WordNumber(50, is_prefixed=True)),
        ("quatre-vingt-dix", "fr", WordNumber(90)),
        ("п'ятдесят", "uk", WordNumber(50)),
        ("пятьдесят", "ru", WordNumber(50)),
        ("veinticinco", "es", WordNumber(25)),
    ],
)
def test_one_word_reads_as_its_number(
    word: str, language: str, expected: WordNumber
) -> None:
    assert read_word_number(fold_word(word), NUMBER_WORDS[language]) == expected


@pytest.mark.parametrize(
    ("word", "language"),
    [
        ("often", "en"),
        ("und", "de"),
        ("-fünf", "de"),
        ("fünfund", "de"),
        ("yüzde", "tr"),
        ("ორშაბათი", "ka"),
        ("de", "tr"),
    ],
)
def test_other_words_are_no_numbers(word: str, language: str) -> None:
    assert read_word_number(fold_word(word), NUMBER_WORDS[language]) is None


def test_words_are_folded_before_lookup() -> None:
    assert fold_word("ПЯТЬ") == "пять"
    assert fold_word("трёх") == "трех"
    assert fold_word("п’ять") == fold_word("пʼять") == "п'ять"
    assert fold_word("أربعين") == "اربعين"


def test_a_word_of_joiners_only_has_no_value() -> None:
    assert add_parts(["-"], NUMBER_WORDS["en"]) is None


def test_merged_lexicons_keep_the_first_language_value() -> None:
    first = NumberWordLexicon(values={"x": 1}, multipliers={"y": 100})
    second = NumberWordLexicon(values={"x": 2, "y": 3}, is_tens_before_teens=True)

    merged = merge_lexicons([first, second])

    assert merged.values == {"x": 1, "y": 3}
    assert merged.multipliers == {}
    assert merged.is_tens_before_teens is True


def test_the_same_languages_share_one_lexicon() -> None:
    assert number_words_for(["en", "ru", "xx"]) is number_words_for(["en", "ru"])


@pytest.mark.parametrize(
    ("text", "values"),
    [
        ("ten fifty", [10, 50]),
        ("fifty five", [55]),
        ("five fifty", [5, 50]),
        ("hundred hundred", [100, 100]),
        ("two hundred three", [203]),
        ("two hundred three hundred", [203, 100]),
        ("thousand thousand", [1000, 1000]),
        ("two million three hundred thousand", [2_300_000]),
        ("a lari", []),
        ("a", []),
        # "1,500" may be 1500 or 1.5: only the bare multiplier is read.
        ("1,500 thousand", [1000]),
        ("2 lari", []),
        ("eleven five", [11, 5]),
    ],
)
def test_runs_join_words_only_in_a_valid_order(text: str, values: list[int]) -> None:
    runs = find_number_runs(tokenize(text), NUMBER_WORDS["en"])

    assert [int(run.value) for run in runs] == values


def test_teens_after_tens_need_french() -> None:
    english = find_number_runs(tokenize("sixty eleven"), NUMBER_WORDS["en"])
    french = find_number_runs(tokenize("soixante onze"), NUMBER_WORDS["fr"])

    assert [int(run.value) for run in english] == [60, 11]
    assert [int(run.value) for run in french] == [71]


def test_units_before_tens_need_a_joining_and() -> None:
    joined = find_number_runs(tokenize("خمسة وعشرون"), NUMBER_WORDS["ar"])
    bare = find_number_runs(tokenize("خمسة عشرون"), NUMBER_WORDS["ar"])

    assert [int(run.value) for run in joined] == [25]
    assert [int(run.value) for run in bare] == [5, 20]


def test_a_currency_symbol_before_words_makes_money() -> None:
    (mention,) = mentions("Only $ fifty today.", "USD", "en")

    assert mention.is_money is True
    assert mention.text == "$ fifty"


def test_a_lower_case_word_before_words_is_no_currency() -> None:
    assert mentions("lari fifty", "GEL", "en") == []


def test_a_bare_multiplier_with_a_currency_is_money() -> None:
    (mention,) = mentions("A thousand lari, not thousand lari.", "GEL", "en")[:1]

    assert sorted(mention.amounts) == [1000]


def test_hours_outside_the_day_are_no_times() -> None:
    assert mentions("We open at thirty.", "GEL", "en") == []
