"""
Uzbek written in Cyrillic (ҳ, ў, қ, ғ and its frequent words) is read as
Uzbek, not as Kazakh, Belarusian or Russian, whose letters it shares.
"""

import pytest

from app.schemas.dto.language_detection import DetectedLanguage
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.language_detector import LanguageDetector

DETECTOR = LanguageDetector()

# The language probe: what Uzbek visitors write first, in Cyrillic.
UZBEK_CYRILLIC_PROBES: list[str] = [
    "Ассалому алайкум, эртага кечқурун икки кишилик стол банд қилмоқчиман",
    "Салом, нархи қанча?",
    "Раҳмат!",
    "Ҳа, яхши",
    "Бугун очиқми?",
    "Йўқ, эртага келаман",
    "Сизларда жой борми?",
]


def detect(
    text: str,
    business_languages: tuple[str, ...],
    conversation_language: str | None,
) -> DetectedLanguage:
    return DETECTOR.detect_any(
        MessageText(text),
        [LanguageTag(tag) for tag in business_languages],
        LanguageTag(business_languages[0]),
        None if conversation_language is None else LanguageTag(conversation_language),
        None,
    )


@pytest.mark.parametrize("text", UZBEK_CYRILLIC_PROBES)
@pytest.mark.parametrize("business_languages", [("ka", "ru", "en"), ("uz", "ru")])
@pytest.mark.parametrize("conversation_language", [None, "ru", "uz"])
def test_uzbek_in_cyrillic_is_read_as_uzbek_in_cyrillic(
    text: str,
    business_languages: tuple[str, ...],
    conversation_language: str | None,
) -> None:
    detected = detect(text, business_languages, conversation_language)

    assert detected.language == "uz-Cyrl"
    assert detected.is_read_from_text


def test_a_business_writing_uzbek_in_cyrillic_keeps_its_own_tag() -> None:
    detected = detect("Салом, нархи қанча?", ("uz-Cyrl", "ru"), None)

    assert detected.language == "uz-Cyrl"


def test_latin_uzbek_stays_uzbek_in_latin_after_a_cyrillic_message() -> None:
    detected = detect(
        "Assalomu alaykum, ertaga stol band qilmoqchiman", ("uz", "ru"), "uz-Cyrl"
    )

    assert detected.language == "uz"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Its neighbours keep their own letters and words.
        ("Сәлеметсіз бе, ертең кешке екі адамға үстел брондағым келеді", "kk"),
        ("Добры дзень, ці можна заказаць столік на заўтра?", "be"),
        ("Здравствуйте, можно столик на завтра?", "ru"),
        ("Стол на двоих", "ru"),
        ("Спасибо", "ru"),
    ],
)
def test_kazakh_belarusian_and_russian_are_not_taken_for_uzbek(
    text: str, expected: str
) -> None:
    for conversation_language in (None, "ru"):
        assert detect(text, ("ka", "ru", "en"), conversation_language).language == (
            expected
        )
