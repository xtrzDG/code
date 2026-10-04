"""
Any language a customer writes in, also outside the business languages,
with the conversation's language kept when a message tells too little.
The cases of the language probe of assessment 2 are the first tests.
"""

import pytest

from app.schemas.dto.language_detection import DetectedLanguage
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.language_detector import LanguageDetector

DETECTOR = LanguageDetector()
GEORGIAN_BUSINESS: list[LanguageTag] = [
    LanguageTag("ka"),
    LanguageTag("ru"),
    LanguageTag("en"),
]


def detect(
    text: str,
    conversation_language: str | None = None,
    contact_language: str | None = None,
    version_languages: list[LanguageTag] | None = None,
    default_language: str = "ka",
) -> DetectedLanguage:
    return DETECTOR.detect_any(
        MessageText(text),
        GEORGIAN_BUSINESS if version_languages is None else version_languages,
        LanguageTag(default_language),
        None if conversation_language is None else LanguageTag(conversation_language),
        None if contact_language is None else LanguageTag(contact_language),
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("שלום, יש מקום?", "he"),
        ("Hallo, haben Sie heute Abend einen Tisch frei?", "de"),
        ("مرحبا، هل لديكم طاولة؟", "ar"),
        ("Ի՞նչ արժե", "hy"),
        ("Привіт, є столик?", "uk"),
        ("Bonjour, une table pour deux?", "fr"),
        ("Salam, masa var?", "az"),
    ],
)
def test_languages_outside_the_business_languages_are_read(
    text: str, expected: str
) -> None:
    for conversation_language in (None, "ka", "ru"):
        detected = detect(text, conversation_language)

        assert detected.language == expected
        assert detected.script_hint is None
        assert detected.is_read_from_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("gamarjoba, magida mchirdeba 4 kacze xval", "ka"),
        ("gamarjobat, xval saghamos magida gaqvt?", "ka"),
        ("ramdeni ghirs?", "ka"),
        ("privet, mozhno stolik na dvoih?", "ru"),
        ("zdravstvuyte, skolko stoit?", "ru"),
        ("pryvit, mozhna stolyk na zavtra?", "uk"),
        ("barev dzez, qani arje?", "hy"),
        ("shalom, yesh makom le shnayim machar?", "he"),
    ],
)
def test_languages_typed_in_latin_letters_are_read_with_a_script_hint(
    text: str, expected: str
) -> None:
    detected = detect(text)

    assert detected.language == expected
    assert detected.script_hint == "Latn"
    assert detected.is_read_from_text


@pytest.mark.parametrize("text", ["ok", "OK!", "👍", "4", "+995 555 12 34 56", "ахаха"])
def test_messages_without_words_keep_the_conversation_language(text: str) -> None:
    for conversation_language in ("ru", "he", "zh"):
        detected = detect(text, conversation_language)

        assert detected.language == conversation_language
        assert not detected.is_read_from_text


def test_without_a_conversation_language_the_contact_then_the_default_is_kept() -> None:
    assert detect("👍", contact_language="de").language == "de"
    assert detect("👍", conversation_language="ru", contact_language="de").language == (
        "ru"
    )
    assert detect("👍").language == "ka"


@pytest.mark.parametrize("text", ["Merci", "Danke", "thanks", "gmadlobt", "Pizza?"])
def test_one_foreign_word_does_not_switch_a_conversation(text: str) -> None:
    detected = detect(text, "ru")

    assert detected.language == "ru"
    assert not detected.is_read_from_text


def test_a_single_word_starts_a_conversation_in_its_language() -> None:
    assert detect("Merci").language == "fr"
    assert detect("Danke").language == "de"
    assert detect("gmadlobt").language == "ka"


def test_a_script_the_conversation_language_is_not_written_in_switches_at_once() -> (
    None
):
    assert detect("да", "ka").language == "ru"
    assert detect("Спасибо!", "ka").language == "ru"
    assert detect("დიახ", "ru").language == "ka"
    assert detect("תודה", "en").language == "he"


def test_latin_words_without_evidence_keep_a_non_latin_conversation() -> None:
    assert detect("iPhone 15 Pro?", "zh").language == "zh"
    assert detect("Wi-Fi?", "ka").language == "ka"


def test_a_conversation_in_transliteration_keeps_its_hint() -> None:
    detected = detect("kargi, madloba", "ka")

    assert detected.language == "ka"
    assert detected.script_hint == "Latn"


def test_clear_evidence_switches_a_conversation() -> None:
    assert detect("Thank you, see you tomorrow at 7", "ru").language == "en"
    assert detect("Привіт", "ru").language == "uk"
    assert detect("Здравствуйте, можно столик на завтра?", "uk").language == "ru"


def test_a_message_in_the_kept_language_is_read_from_the_text() -> None:
    detected = detect("Спасибо, до завтра", "ru")

    assert detected.language == "ru"
    assert detected.is_read_from_text


def test_latin_text_without_evidence_starts_in_a_latin_business_language() -> None:
    assert detect("Pizza?").language == "en"
    assert not detect("Pizza?").is_read_from_text
    assert detect("Pizza?", version_languages=[LanguageTag("ka")]).language == "ka"


def test_the_business_tag_of_a_language_is_returned() -> None:
    business = [LanguageTag("es"), LanguageTag("pt-BR"), LanguageTag("no")]

    assert detect("Obrigado, quanto custa?", version_languages=business).language == (
        "pt-BR"
    )
    assert (
        detect(
            "Hei, jeg vil gjerne bestille et bord i morgen", version_languages=business
        ).language
        == "no"
    )
    assert detect("Obrigado, quanto custa?", "pt-PT").language == "pt-PT"


def test_han_text_keeps_a_japanese_conversation_and_is_chinese_otherwise() -> None:
    assert detect("明天", "ja").language == "ja"
    assert detect("明天晚上").language == "zh"
    assert detect("明天晚上", version_languages=[LanguageTag("zh-Hant")]).language == (
        "zh-Hant"
    )
    assert detect("明日の予約です").language == "ja"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("நாளை இரவு இரண்டு பேருக்கு மேசை வேண்டும்", "ta"),
        ("ነገ ጠረጴዛ ማስያዝ እፈልጋለሁ", "am"),
        ("नमस्ते, मुझे कल के लिए टेबल चाहिए", "hi"),
        ("नमस्कार, उद्या टेबल हवे आहे", "mr"),
    ],
)
def test_other_scripts_name_their_language(text: str, expected: str) -> None:
    assert detect(text).language == expected


def test_a_business_language_of_a_single_language_script_wins_ties() -> None:
    assamese_business = [LanguageTag("as"), LanguageTag("en")]

    assert detect("আমি কাল টেবিল চাই", version_languages=assamese_business).language == (
        "as"
    )
