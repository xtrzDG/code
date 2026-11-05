"""
Every language the AI disclosure is written in is recognized: a customer
who writes it gets the disclosure, the platform's notices and the reply in
it, also when the business did not list the language.
"""

import pytest

from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.assistant_texts.ai_disclosure_texts import (
    AI_DISCLOSURE,
)
from app.utilities.conversations.language_detector import LanguageDetector
from app.utilities.conversations.language_scoring import evidence_code
from tests.brain.any_language_samples import FIRST_MESSAGES

DETECTOR = LanguageDetector()
GEORGIAN_BUSINESS: list[LanguageTag] = [
    LanguageTag("ka"),
    LanguageTag("ru"),
    LanguageTag("en"),
]


def test_every_disclosure_language_has_a_sample_message() -> None:
    disclosure_codes: set[str] = {
        evidence_code(language) for language in AI_DISCLOSURE.values
    }

    assert disclosure_codes == set(FIRST_MESSAGES)


@pytest.mark.parametrize(("language", "text"), sorted(FIRST_MESSAGES.items()))
@pytest.mark.parametrize("conversation_language", [None, "ru", "en"])
def test_a_first_message_is_read_in_its_language(
    language: str, text: str, conversation_language: str | None
) -> None:
    detected = DETECTOR.detect_any(
        MessageText(text),
        GEORGIAN_BUSINESS,
        LanguageTag("ka"),
        None if conversation_language is None else LanguageTag(conversation_language),
        None,
    )

    assert detected.language == language
    assert detected.is_read_from_text
