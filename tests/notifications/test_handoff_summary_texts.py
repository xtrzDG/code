"""Summaries of platform-made handoffs in the reader's language."""

from pathlib import Path

import pytest

from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.constants.localization import CABINET_LANGUAGES
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

CABINET_LANGUAGE_TAGS: tuple[str, ...] = tuple(
    language.value for language in CABINET_LANGUAGES
)
CABINET_DICTIONARIES: Path = (
    Path(__file__).resolve().parents[2] / "web/src/i18n/messages/sections/insights"
)
# Every cabinet language whose handoffs dictionary the web has.
CABINET_DICTIONARY_LANGUAGES: tuple[str, ...] = tuple(
    language
    for language in CABINET_LANGUAGE_TAGS
    if (CABINET_DICTIONARIES / f"handoffs.{language}.ts").exists()
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


def test_every_code_has_a_text_in_every_cabinet_language() -> None:
    assert set(SUMMARY_TEXTS) == set(HandoffSummaryCode)
    for texts in (SUMMARY_TEXTS, SUMMARY_TEXTS_WITH_VALUES):
        for code, text in texts.items():
            assert {str(tag) for tag in text.values} == set(CABINET_LANGUAGE_TAGS), code


@pytest.mark.parametrize("code", sorted(SUMMARY_TEXTS_WITH_VALUES))
def test_values_fill_their_place_in_every_language(code: HandoffSummaryCode) -> None:
    for language in CABINET_LANGUAGE_TAGS:
        text = render(code, language, values=("30 lari", "21:45"))
        # Right-to-left texts isolate the values inside the brackets.
        assert "30 lari, 21:45" in text, (code, language)
        assert "{" not in text


def test_the_customer_message_is_quoted_in_the_readers_style() -> None:
    assert render(
        HandoffSummaryCode.MODEL_UNAVAILABLE, "it", "Posso portare il cane?"
    ) == (
        "L'assistente non è stato disponibile per qualche istante e non ha potuto "
        "rispondere. Il messaggio del cliente: “Posso portare il cane?”"
    )
    assert render(HandoffSummaryCode.ANSWER_UNFINISHED, "en", "Hi {there}") == (
        "The assistant could not finish its answer. "
        "The customer's message: “Hi {there}”"
    )
    # Georgian is not in the catalog: the owner reads English, the quote stays.
    assert render(HandoffSummaryCode.MODEL_DECLINED, "ka", "გამარჯობა") == (
        "The assistant would not answer this message. "
        "The customer's message: “გამარჯობა”"
    )


def test_an_undelivered_reply_quotes_the_reply() -> None:
    assert render(HandoffSummaryCode.REPLY_UNDELIVERED, "it", "Il tavolo è libero") == (
        "La risposta dell'assistente non è arrivata al cliente. Contattalo in un "
        "altro modo. La risposta: “Il tavolo è libero”"
    )


def test_without_values_the_sentence_stays_whole() -> None:
    assert render(HandoffSummaryCode.CALL_REQUEST_UNVERIFIED_VALUES, "en") == (
        "On the call the assistant named figures that are not in your business "
        "details. Check the request from this call against the transcript."
    )
    assert render(HandoffSummaryCode.DATA_ERASED, "it") == (
        "Dati cancellati su richiesta del cliente."
    )


def test_italian_owners_read_their_language() -> None:
    assert render(HandoffSummaryCode.MODEL_DECLINED, "it") == (
        "L'assistente non ha voluto rispondere a questo messaggio."
    )
    assert render(HandoffSummaryCode.UNVERIFIED_VALUES, "it", "Ciao", ("50 €",)) == (
        "L'assistente non ha inviato una risposta con cifre o affermazioni che non "
        "risultano nei dati della tua attività (50 €). "
        "Il messaggio del cliente: “Ciao”"
    )


def test_other_languages_read_english() -> None:
    assert render(HandoffSummaryCode.MODEL_DECLINED, "fr") == (
        "The assistant would not answer this message."
    )
    arabic = render(HandoffSummaryCode.UNVERIFIED_VALUES, "ar", "مرحبا", ("50 ₪",))
    assert arabic.startswith("The assistant held back")
    assert "50 ₪" in arabic


@pytest.mark.parametrize("language", CABINET_DICTIONARY_LANGUAGES)
def test_the_cabinet_shows_the_same_words_as_the_notifications(language: str) -> None:
    dictionary: str = (CABINET_DICTIONARIES / f"handoffs.{language}.ts").read_text(
        encoding="utf-8"
    )
    for code, text in SUMMARY_TEXTS.items():
        assert f'"{text.values[LanguageTag(language)]}"' in dictionary, code
    for code, text in SUMMARY_TEXTS_WITH_VALUES.items():
        assert f'"{text.values[LanguageTag(language)]}"' in dictionary, code
