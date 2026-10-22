"""What a declined call's transcript keeps: the words, not how to reach or bill."""

import pytest

from app.schemas.constants.conversations import MessageAuthor
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine
from app.schemas.typings.channels.constrained_integers import CallOffsetSeconds
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.calls.call_summary_prompt import read_call_memory
from app.utilities.calls.call_transcript_redaction import redact_call_text
from app.utilities.channels.call_outcomes import render_call_transcript


@pytest.mark.parametrize(
    ("said", "kept"),
    [
        ("My number is +995 599 12 34 56.", "My number is [phone]."),
        ("Call 0599123456 please", "Call [phone] please"),
        ("Mail nino.b@example.ge today", "Mail [email] today"),
        ("Card 4111 1111 1111 1111 exp 12/28", "Card [card number] exp 12/28"),
        ("Card 4111-1111-1111-1111", "Card [card number]"),
        ("IBAN GE29 NB00 0000 0101 9049 17", "IBAN [account number]"),
        ("Pay to GE29NB0000000101904917", "Pay to [account number]"),
    ],
)
def test_identifiers_become_placeholders(said: str, kept: str) -> None:
    assert redact_call_text(said) == kept


@pytest.mark.parametrize(
    "said",
    [
        "A table for 4 on 2026-10-03 at 19:30.",
        "It costs 45 GEL, room 204, for 3 nights.",
        "Saturday at 8, please, by the window.",
    ],
)
def test_what_was_agreed_stays(said: str) -> None:
    assert redact_call_text(said) == said


def test_only_a_declined_call_is_rendered_redacted() -> None:
    lines = [
        FinishedCallTranscriptLine(
            author=MessageAuthor.CUSTOMER,
            text=MessageText("I am at nino@example.ge"),
            offset_seconds=CallOffsetSeconds(65),
        )
    ]

    assert str(render_call_transcript(lines)) == (
        "[01:05] customer: I am at nino@example.ge"
    )
    assert str(render_call_transcript(lines, is_recording_declined=True)) == (
        "[01:05] customer: I am at [email]"
    )


@pytest.mark.parametrize(
    ("answer", "memory"),
    [
        ('{"en": "x", "memory": "Booked a table for 4."}', "Booked a table for 4."),
        ('{"memory": "Call back on +995 599 12 34 56."}', "Call back on [phone]."),
        ('{"memory": "Write to a@b.ge."}', "Write to [email]."),
    ],
)
def test_the_memory_is_read_without_contact_details(answer: str, memory: str) -> None:
    assert str(read_call_memory(answer)) == memory


@pytest.mark.parametrize("answer", ['{"en": "x"}', '{"memory": " "}', "not json", None])
def test_an_answer_without_a_memory_remembers_nothing(answer: str | None) -> None:
    assert read_call_memory(answer) is None
