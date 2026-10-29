"""The pieces of the customer memory: prompts, lines, schedules, tool selection."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.conversations.tool_selection import with_list_my_bookings
from app.utilities.memory.conversation_summary_prompt import (
    MAX_TRANSCRIPT_CHARACTERS,
    build_summary_request_text,
    read_conversation_summary,
)
from app.utilities.memory.summary_jobs import (
    SUMMARY_IDLE_MICROSECONDS,
    decode_summary_payload,
    starts_active_period,
    summary_due_at,
)

TOOLS = AssistantToolName


def test_versions_assembled_before_the_tool_offer_it_after_their_booking_tools() -> (
    None
):
    assert with_list_my_bookings(
        [TOOLS.CHECK_AVAILABILITY, TOOLS.CANCEL_BOOKING, TOOLS.RESCHEDULE_BOOKING,
         TOOLS.CREATE_LEAD]
    ) == [
        TOOLS.CHECK_AVAILABILITY,
        TOOLS.CANCEL_BOOKING,
        TOOLS.RESCHEDULE_BOOKING,
        TOOLS.LIST_MY_BOOKINGS,
        TOOLS.CREATE_LEAD,
    ]  # fmt: skip
    assert with_list_my_bookings([TOOLS.CANCEL_BOOKING, TOOLS.CREATE_LEAD]) == [
        TOOLS.CANCEL_BOOKING,
        TOOLS.LIST_MY_BOOKINGS,
        TOOLS.CREATE_LEAD,
    ]


def test_versions_that_do_not_book_or_already_list_stay_as_they_are() -> None:
    leads_only = [TOOLS.SEARCH_KNOWLEDGE, TOOLS.CREATE_LEAD]
    current = [TOOLS.CANCEL_BOOKING, TOOLS.LIST_MY_BOOKINGS]

    assert with_list_my_bookings(leads_only) == leads_only
    assert with_list_my_bookings(current) == current


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (None, None),
        ("   \n ", None),
        ('"Asked about the terrace."', "Asked about the terrace."),
        ("Summary: Booked a table\nfor 4.", "Booked a table for 4."),
        ("«Спросил про террасу.»", "Спросил про террасу."),
    ],
)
def test_the_summary_is_read_as_one_clean_line(
    answer: str | None, expected: str | None
) -> None:
    summary = read_conversation_summary(answer)

    assert (None if summary is None else str(summary)) == expected


def test_a_long_summary_is_cut_at_a_word() -> None:
    summary = read_conversation_summary("word " * 100)

    assert summary is not None
    assert len(str(summary)) <= 300
    assert str(summary).endswith("word…")


def test_a_long_conversation_is_cut_in_the_middle() -> None:
    lines = [(MessageAuthor.CUSTOMER, f"message {index} " * 20) for index in range(100)]

    text = build_summary_request_text("Sakhli", lines)

    assert text.startswith("Business: Sakhli\nConversation:\nCustomer: message 0")
    assert "[...]" in text
    assert "message 99" in text
    assert len(text) < MAX_TRANSCRIPT_CHARACTERS + 100


def test_a_summary_is_due_two_quiet_hours_after_the_latest_message() -> None:
    assert int(summary_due_at(Microseconds(5))) == 5 + SUMMARY_IDLE_MICROSECONDS
    assert starts_active_period(None, Microseconds(10))
    assert starts_active_period(
        Microseconds(0), Microseconds(SUMMARY_IDLE_MICROSECONDS)
    )
    assert not starts_active_period(
        Microseconds(1), Microseconds(SUMMARY_IDLE_MICROSECONDS)
    )


def test_a_job_payload_without_a_conversation_is_refused() -> None:
    with pytest.raises(ValidationFailedError):
        decode_summary_payload(JobPayloadJson('{"booking_id": "x"}'))
