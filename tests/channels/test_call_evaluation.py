"""
The voice platform's own evaluation of a call (booking_correct,
disclosure_said and the data collection fields) is kept with the call and
read by the audit after it.
"""

import logging
from typing import Any

import pytest

from app.schemas.constants.calls import CallEvaluationResult
from app.schemas.constants.conversations import CallGuardVerdict
from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.dto.handoffs import CodedHandoffSummary
from app.schemas.typings.conversations.strings import UnverifiedReplyValue
from tests.channels.post_call_steps import (
    add_booking,
    post_call,
    post_call_payload,
    stored_calls,
)
from tests.channels.voice_setup import build_voice_setup


def evaluated_call(
    booking_correct: str,
    disclosure_said: str = "success",
    collected: dict[str, object] | None = None,
) -> dict[str, Any]:
    payload = post_call_payload(tool_names=("create_booking",))
    payload["data"]["transcript"] = [
        {
            "role": "agent",
            "message": "AI assistant of Funicular VR.",
            "time_in_call_secs": 0,
        },
        {
            "role": "user",
            "message": "A session on Saturday please.",
            "time_in_call_secs": 5,
        },
        {"role": "agent", "message": "Booked for Saturday.", "time_in_call_secs": 9},
    ]
    payload["data"]["analysis"] = {
        "call_successful": "success",
        "transcript_summary": "A booking.",
        "evaluation_criteria_results": {
            "booking_correct": {
                "criteria_id": "booking_correct",
                "result": booking_correct,
                "rationale": "-",
            },
            "disclosure_said": {
                "criteria_id": "disclosure_said",
                "result": disclosure_said,
                "rationale": "-",
            },
        },
        "data_collection_results": {
            name: {"data_collection_id": name, "value": value, "rationale": "-"}
            for name, value in (collected or {}).items()
        },
    }
    return payload


def test_the_evaluation_is_kept_with_the_call() -> None:
    setup = build_voice_setup()
    add_booking(setup)

    post_call(
        setup,
        evaluated_call(
            "success",
            collected={
                "booking_date": "2026-10-03",
                "booking_time": "8 pm",
                "party_size": 4.0,
            },
        ),
    )

    [call] = stored_calls(setup)
    assert call.analysis is not None
    assert call.analysis.booking_correct is CallEvaluationResult.SUCCESS
    assert call.analysis.disclosure_said is CallEvaluationResult.SUCCESS
    assert call.analysis.callback_requested is None
    assert str(call.analysis.booking_date) == "2026-10-03"
    # A time in another shape than HH:MM is left out, a whole 4.0 is 4.
    assert call.analysis.booking_time is None
    assert call.analysis.party_size == 4
    assert call.guard_verdict is CallGuardVerdict.CLEAN
    assert setup.testbed.call_handoff.commands == []


def test_a_booking_the_platform_found_wrong_goes_to_staff_with_the_request() -> None:
    setup = build_voice_setup()
    add_booking(setup)

    post_call(
        setup,
        evaluated_call(
            "failure",
            collected={
                "booking_date": "2026-10-03",
                "booking_time": "20:00",
                "party_size": 4,
            },
        ),
    )

    [call] = stored_calls(setup)
    assert call.guard_verdict is CallGuardVerdict.HANDED_OFF
    [command] = setup.testbed.call_handoff.commands
    summary = command.summary
    assert isinstance(summary, CodedHandoffSummary)
    assert summary.code is HandoffSummaryCode.CALL_BOOKING_UNVERIFIED_VALUES
    assert summary.flagged_values == [
        UnverifiedReplyValue("2026-10-03"),
        UnverifiedReplyValue("20:00"),
        UnverifiedReplyValue("4 people"),
    ]


def test_a_wrong_booking_without_details_still_reaches_staff() -> None:
    setup = build_voice_setup()
    add_booking(setup)

    post_call(setup, evaluated_call("failure"))

    [command] = setup.testbed.call_handoff.commands
    summary = command.summary
    assert isinstance(summary, CodedHandoffSummary)
    assert summary.flagged_values == [
        UnverifiedReplyValue("booking does not match the request")
    ]


def test_a_failure_in_a_call_without_a_booking_opens_nothing() -> None:
    setup = build_voice_setup()

    post_call(setup, evaluated_call("failure"))

    [call] = stored_calls(setup)
    assert call.guard_verdict is CallGuardVerdict.CLEAN
    assert setup.testbed.call_handoff.commands == []


def test_a_missing_disclosure_is_logged_without_the_caller(
    caplog: pytest.LogCaptureFixture,
) -> None:
    setup = build_voice_setup()

    with caplog.at_level(logging.WARNING, logger="app"):
        post_call(setup, evaluated_call("unknown", disclosure_said="failure"))

    [call] = stored_calls(setup)
    assert call.analysis is not None
    assert call.analysis.disclosure_said is CallEvaluationResult.FAILURE
    [record] = [
        record for record in caplog.records if "AI disclosure" in record.getMessage()
    ]
    assert str(call.id) in record.getMessage()
    assert "+995" not in record.getMessage()
