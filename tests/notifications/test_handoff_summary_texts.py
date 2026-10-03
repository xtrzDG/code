"""Summaries of platform-made handoffs in the reader's language."""

from pathlib import Path

import pytest

from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.dto.handoffs import CodedHandoffSummary, HandoffSummaryInput
from app.schemas.typings.conversations.strings import UnverifiedReplyValue
from app.schemas.typings.handoffs.strings import HandoffQuotedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.handoff_summary_texts import (
    SUMMARY_TEXTS,
    SUMMARY_TEXTS_WITH_VALUES,
)
from app.transformers.notifications.handoff_summary_transformer import (
    HandoffSummaryTransformer,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver

STAFF_LANGUAGES: tuple[str, ...] = ("en", "ru", "ka")
CABINET_DICTIONARIES: Path = (
    Path(__file__).resolve().parents[2] / "web/src/i18n/messages/sections/insights"
)


def render(
    code: HandoffSummaryCode,
    language: str,
    quoted: str | None = None,
    values: tuple[str, ...] = (),
) -> str:
    summary = CodedHandoffSummary(
        code=code,
        quoted_text=None if quoted is None else HandoffQuotedText(quoted),
        flagged_values=[UnverifiedReplyValue(value) for value in values],
    )
    return str(
        HandoffSummaryTransformer(LocalizedTextResolver()).transform(
            HandoffSummaryInput(summary=summary, language=LanguageTag(language))
        )
    )


def test_every_code_has_a_text_in_every_staff_language() -> None:
    assert set(SUMMARY_TEXTS) == set(HandoffSummaryCode)
    for texts in (SUMMARY_TEXTS, SUMMARY_TEXTS_WITH_VALUES):
        for code, text in texts.items():
            assert {str(tag) for tag in text.values} == set(STAFF_LANGUAGES), code


@pytest.mark.parametrize("code", sorted(SUMMARY_TEXTS_WITH_VALUES))
def test_values_fill_their_place_in_every_language(code: HandoffSummaryCode) -> None:
    for language in STAFF_LANGUAGES:
        text = render(code, language, values=("30 lari", "21:45"))
        assert "(30 lari, 21:45)" in text, (code, language)
        assert "{" not in text


def test_the_customer_message_is_quoted_in_the_readers_style() -> None:
    assert render(HandoffSummaryCode.MODEL_UNAVAILABLE, "ru", "Можно с собакой?") == (
        "Помощник был временно недоступен и не смог ответить. "
        "Сообщение клиента: «Можно с собакой?»"
    )
    assert render(HandoffSummaryCode.MODEL_DECLINED, "ka", "გამარჯობა") == (
        "ასისტენტმა ამ შეტყობინებას პასუხი არ გასცა. კლიენტის შეტყობინება: „გამარჯობა“"
    )
    assert render(HandoffSummaryCode.ANSWER_UNFINISHED, "en", "Hi {there}") == (
        "The assistant could not finish its answer. "
        "The customer's message: “Hi {there}”"
    )


def test_an_undelivered_reply_quotes_the_reply() -> None:
    assert render(HandoffSummaryCode.REPLY_UNDELIVERED, "ru", "Столик свободен") == (
        "Ответ помощника не дошёл до клиента. Свяжитесь с ним другим способом. "
        "Ответ: «Столик свободен»"
    )


def test_without_values_the_sentence_stays_whole() -> None:
    assert render(HandoffSummaryCode.CALL_REQUEST_UNVERIFIED_VALUES, "en") == (
        "On the call the assistant named figures that are not in your business "
        "details. Check the request from this call against the transcript."
    )
    assert render(HandoffSummaryCode.DATA_ERASED, "ka") == (
        "მონაცემები წაიშალა კლიენტის თხოვნით."
    )


def test_other_languages_read_english() -> None:
    assert render(HandoffSummaryCode.MODEL_DECLINED, "de") == (
        "The assistant would not answer this message."
    )
    hebrew = render(HandoffSummaryCode.UNVERIFIED_VALUES, "he", "שלום", ("50 ₪",))
    assert hebrew.startswith("The assistant held back")
    assert "(50 ₪)" in hebrew


@pytest.mark.parametrize("language", STAFF_LANGUAGES)
def test_the_cabinet_shows_the_same_words_as_the_notifications(language: str) -> None:
    dictionary: str = (
        CABINET_DICTIONARIES / f"handoffs.{language}.ts"
    ).read_text(encoding="utf-8")
    for code, text in SUMMARY_TEXTS.items():
        assert f'"{text.values[LanguageTag(language)]}"' in dictionary, code
    for code, text in SUMMARY_TEXTS_WITH_VALUES.items():
        assert f'"{text.values[LanguageTag(language)]}"' in dictionary, code
