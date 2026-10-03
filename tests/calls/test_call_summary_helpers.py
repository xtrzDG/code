"""
What the summary model is asked and how its answer is read; the languages
of a summary; reading a call the voice platform could not start.
"""

import json

import pytest

from app.adapters.voice.elevenlabs_voice_webhook_adapter import (
    ElevenLabsVoiceWebhookAdapter,
)
from app.schemas.constants.calls import MissedCallReason
from app.schemas.constants.conversations import CallOutcome, MessageAuthor
from app.schemas.domain.conversations import CallSummary
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.channels.constrained_integers import CallOffsetSeconds
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.voice.summaries.call_summary_writer import (
    pick_summary,
    summary_languages,
)
from app.utilities.calls.call_summary_prompt import (
    MAX_SUMMARY_CHARACTERS,
    MAX_TRANSCRIPT_CHARACTERS,
    OMISSION_MARK,
    build_call_summary_request_text,
    read_call_summaries,
    render_transcript,
    shorten_summary,
)
from app.utilities.calls.text_back_jobs import decode_text_back_payload
from tests.calls.call_steps import failed_start_payload
from tests.channels.channels_settings import build_settings
from tests.channels.voice_setup import build_voice_setup

EN: LanguageTag = LanguageTag("en")
RU: LanguageTag = LanguageTag("ru")


def line(author: MessageAuthor, text: str) -> FinishedCallTranscriptLine:
    return FinishedCallTranscriptLine(
        author=author, text=MessageText(text), offset_seconds=CallOffsetSeconds(0)
    )


class TestSummaryRequest:
    def test_the_request_names_languages_outcome_and_speakers(self) -> None:
        text = build_call_summary_request_text(
            "Funicular VR",
            CallOutcome.BOOKING,
            [EN, RU],
            [
                line(MessageAuthor.ASSISTANT, "Hello!"),
                line(MessageAuthor.CUSTOMER, "A table for four."),
            ],
        )

        assert text.split("\n") == [
            "Languages: en, ru",
            "Business: Funicular VR",
            "Outcome recorded by the platform: booking",
            "Transcript:",
            "Assistant: Hello!",
            "Caller: A table for four.",
        ]
        assert "unknown" in build_call_summary_request_text("B", None, [EN], [])

    def test_a_long_transcript_keeps_its_start_and_end(self) -> None:
        lines = [
            line(MessageAuthor.CUSTOMER, f"line {index} " + "x" * 90)
            for index in range(400)
        ]

        text = render_transcript(lines)

        assert len(text) <= MAX_TRANSCRIPT_CHARACTERS + len(OMISSION_MARK) + 2
        assert text.startswith("Caller: line 0 ")
        assert text.endswith("x" * 90)
        assert OMISSION_MARK in text


class TestReadingTheAnswer:
    def test_only_requested_languages_with_text(self) -> None:
        answer = json.dumps({"en": "  Wants   a table. ", "ru": "", "de": "Tisch"})

        assert read_call_summaries(f"```json\n{answer}\n```", [EN, RU]) == {
            EN: CallSummaryText("Wants a table.")
        }

    @pytest.mark.parametrize("answer", [None, "no json here", "{not json}", "[1, 2]"])
    def test_unreadable_answers(self, answer: str | None) -> None:
        assert read_call_summaries(answer, [EN]) == {}

    def test_a_long_summary_is_cut_after_a_sentence(self) -> None:
        sentence = "The caller wants a table for four on Saturday evening. "
        text = shorten_summary(sentence * 20)

        assert len(text) <= MAX_SUMMARY_CHARACTERS
        assert text.endswith("evening.")

    def test_a_long_summary_without_sentences_gets_an_ellipsis(self) -> None:
        text = shorten_summary("word " * 200)

        assert len(text) == MAX_SUMMARY_CHARACTERS
        assert text.endswith("…")


class TestSummaryLanguages:
    def test_the_owner_first_then_staff_at_most_four(self) -> None:
        business = build_voice_setup().business
        staff = [LanguageTag(tag) for tag in ["ru", "ka", "en", "de", "fr"]]

        assert [str(tag) for tag in summary_languages(business, staff)] == [
            "ka",
            "ru",
            "en",
            "de",
        ]

    def test_a_summary_in_the_base_language_serves_a_regional_one(self) -> None:
        summaries = [
            CallSummary(language=EN, text=CallSummaryText("Table for four.")),
            CallSummary(language=LanguageTag("pt-BR"), text=CallSummaryText("Mesa.")),
        ]

        assert pick_summary(summaries, LanguageTag("en-GB")) == summaries[0]
        assert pick_summary(summaries, LanguageTag("pt-BR")) == summaries[1]
        assert pick_summary(summaries, RU) is None


class TestFailedStarts:
    @pytest.fixture
    def adapter(self) -> ElevenLabsVoiceWebhookAdapter:
        return ElevenLabsVoiceWebhookAdapter(build_settings())

    def test_a_failed_start_names_both_numbers(
        self, adapter: ElevenLabsVoiceWebhookAdapter
    ) -> None:
        payload = failed_start_payload()

        report = adapter.parse_call_start_failure(json.dumps(payload).encode())

        assert report is not None
        assert report.reason is MissedCallReason.NOT_STARTED
        assert str(report.caller_number) == "+995599123456"
        assert str(report.assistant_number) == "+995322000000"

    def test_twilio_fields_are_read_too(
        self, adapter: ElevenLabsVoiceWebhookAdapter
    ) -> None:
        payload = failed_start_payload()
        payload["data"]["metadata"] = {
            "type": "twilio",
            "body": {"From": "+995599000001", "To": "+995322000000"},
        }

        report = adapter.parse_call_start_failure(json.dumps(payload).encode())

        assert report is not None
        assert str(report.caller_number) == "+995599000001"

    def test_other_events_are_not_failed_starts(
        self, adapter: ElevenLabsVoiceWebhookAdapter
    ) -> None:
        payload = {**failed_start_payload(), "type": "post_call_audio"}

        assert adapter.parse_call_start_failure(json.dumps(payload).encode()) is None
        assert adapter.parse_call_start_failure(b"not json") is None

    def test_a_failure_without_its_call_is_refused(
        self, adapter: ElevenLabsVoiceWebhookAdapter
    ) -> None:
        payload = failed_start_payload()
        del payload["data"]["conversation_id"]

        with pytest.raises(ValidationFailedError):
            adapter.parse_call_start_failure(json.dumps(payload).encode())


def test_a_text_back_job_must_name_its_missed_call() -> None:
    with pytest.raises(ValidationFailedError):
        decode_text_back_payload(JobPayloadJson('{"missed_call_id": 7}'))
