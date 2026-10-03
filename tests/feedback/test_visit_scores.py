"""Reading a visit rating from a reply: digits, stars and number words."""

import pytest

from app.utilities.feedback.visit_score_words import NUMBER_WORDS
from app.utilities.feedback.visit_scores import parse_visit_score


@pytest.mark.parametrize(
    ("text", "languages", "score"),
    [
        ("5", ["en"], 5),
        ("  4 ", ["en"], 4),
        ("1", ["ka"], 1),
        ("٥", ["ar"], 5),
        ("۴", ["fa"], 4),
        ("५", ["hi"], 5),
        ("５", ["ja"], 5),
        ("5️⃣", ["en"], 5),
        ("4/5", ["en"], 4),
        ("4 / 5", ["en"], 4),
        ("4 out of 5", ["en"], 4),
        ("3 из 5", ["ru"], 3),
        ("5!", ["en"], 5),
        ("5, all great", ["en"], 5),
        ("5 all great", ["en"], 5),
        ("2 - the soup was cold", ["en"], 2),
        ("4 stars", ["en"], 4),
        ("5 звёзд", ["ru"], 5),
        ("5 баллов", ["ru"], 5),
        ("5🙂", ["en"], 5),
        ("⭐⭐⭐⭐", ["en"], 4),
        ("⭐️⭐️⭐️⭐️⭐️", ["en"], 5),
        ("★★★☆☆ ok", ["en"], 3),
        ("🌟🌟", ["en"], 2),
        ("five", ["en"], 5),
        ("Five!!!", ["ru"], 5),
        ("five, thank you", ["en"], 5),
        ("пять", ["ru"], 5),
        ("Пятёрка", ["ru"], 5),
        ("тройка", ["ru"], 3),
        ("пять, всё супер", ["ru"], 5),
        ("чотири", ["uk"], 4),
        ("ხუთი", ["ka"], 5),
        ("სამი", ["ka"], 3),
        ("հինգ", ["hy"], 5),
        ("beş", ["tr"], 5),
        ("fünf", ["de"], 5),
        ("cinq", ["fr"], 5),
        ("cuatro", ["es"], 4),
        ("五", ["zh"], 5),
        ("五星", ["zh"], 5),
        ("חמש", ["he"], 5),
        ("خمسة", ["ar"], 5),
    ],
)
def test_ratings_are_read(text: str, languages: list[str], score: int) -> None:
    assert parse_visit_score(text, languages) == score


@pytest.mark.parametrize(
    ("text", "languages"),
    [
        ("", ["en"]),
        ("Hello", ["en"]),
        ("ok", ["en"]),
        ("0", ["en"]),
        ("6", ["en"]),
        ("10", ["en"]),
        ("10/10", ["en"]),
        ("4.5", ["en"]),
        ("4,5", ["ru"]),
        ("3?", ["en"]),
        ("5 people tomorrow?", ["en"]),
        ("2 people at 7", ["en"]),
        ("5abc", ["en"]),
        ("one more thing", ["en"]),
        ("two of us tomorrow", ["en"]),
        ("пять человек завтра", ["ru"]),
        ("⭐ 5", ["en"]),
        ("⭐⭐⭐⭐⭐⭐", ["en"]),
        ("x" * 301, ["en"]),
        # A word of another language than the conversation's is not read.
        ("ხუთი", ["ru"]),
    ],
)
def test_unclear_replies_are_not_ratings(text: str, languages: list[str]) -> None:
    assert parse_visit_score(text, languages) is None


def test_english_words_count_in_every_conversation() -> None:
    assert parse_visit_score("four", ["ka"]) == 4


def test_the_word_table_covers_fifty_five_languages_with_five_numbers() -> None:
    assert len(NUMBER_WORDS) >= 55
    for language, words in NUMBER_WORDS.items():
        assert len(words) == 5, language
        assert all(form.strip() for number in words for form in number.split("|"))
