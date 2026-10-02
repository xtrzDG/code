"""After a call, what the phone assistant said is checked against the business data."""

from typing import Any

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import (
    CallGuardVerdict,
    ConversationStatus,
    MessageAuthor,
)
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.assistants import BusinessFact
from app.schemas.domain.conversations import MessageDocument, ToolCallRecord
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue
from tests.channels.post_call_steps import (
    add_booking,
    post_call,
    post_call_payload,
    process_call,
    stored_calls,
)
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

SLOTS_RESULT: str = (
    '{"timezone":"Asia/Tbilisi","is_open_on_date":true,'
    '"slots":[{"date":"2026-10-03","time":"19:30"}],'
    '"business_today":"2026-10-01 (Thursday)"}'
)


def priced_setup() -> VoiceSetup:
    """A business whose live version prices a VR session at 45 GEL."""

    setup = build_voice_setup()
    version = setup.testbed.assistant_version_repo.get(
        setup.business.id, setup.conversation.assistant_version_id
    )
    assert version is not None
    version.facts = [
        BusinessFact(
            key=FactKey("package_1"),
            label=FactLabel("Package: VR session"),
            value=FactValue("Price: 45.00 GEL; Duration: 60 minutes"),
        )
    ]
    setup.testbed.assistant_version_repo.save(version)
    return setup


def record_tool_call(setup: VoiceSetup, result_json: str) -> None:
    now = setup.testbed.clock.now_microseconds()
    setup.testbed.message_repo.save(
        MessageDocument(
            conversation_id=setup.conversation.id,
            business_id=setup.business.id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.SYSTEM,
            text=MessageText("Voice agent called check_availability."),
            tool_calls=[
                ToolCallRecord(
                    tool_name=AssistantToolName.CHECK_AVAILABILITY,
                    input_json=LlmToolInputJson("{}"),
                    result_json=LlmToolResultJson(result_json),
                )
            ],
            created_at=now,
            updated_at=now,
        )
    )


def call_with_lines(
    lines: list[tuple[str, str]],
    tool_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    payload = post_call_payload(tool_names=tool_names)
    payload["data"]["transcript"] = [
        {"role": role, "message": text, "time_in_call_secs": 10 * index}
        for index, (role, text) in enumerate(lines)
    ]
    return payload


def test_a_call_that_says_only_backed_values_is_clean() -> None:
    setup = priced_setup()
    record_tool_call(setup, SLOTS_RESULT)
    add_booking(setup)

    post_call(
        setup,
        call_with_lines(
            [
                ("agent", "Hello! This is the AI assistant of Funicular VR."),
                ("user", "How much is a session, and is Saturday free at 8?"),
                ("agent", "A session costs 45 lari. Saturday at 19:30 is free."),
                ("user", "Then 20:00 please, for 4 people."),
                ("agent", "Booked: Saturday 2026-10-03 at 20:00 for 4 people."),
            ],
            tool_names=("check_availability", "create_booking"),
        ),
    )

    [call] = stored_calls(setup)
    assert call.guard_verdict is CallGuardVerdict.CLEAN
    assert call.unverified_values == []
    assert setup.testbed.call_handoff.commands == []


def test_an_invented_price_in_a_booking_call_goes_to_staff() -> None:
    setup = priced_setup()
    add_booking(setup)

    outcome = process_call(
        setup,
        call_with_lines(
            [
                ("user", "Is it cheaper on weekdays?"),
                ("agent", "Yes, on weekdays a session is only 30 lari."),
                ("agent", "So 30 lari, booked for Saturday."),
            ],
            tool_names=("create_booking",),
        ),
    )

    assert outcome["outcome"] == "booking"
    [call] = stored_calls(setup)
    assert call.guard_verdict is CallGuardVerdict.HANDED_OFF
    assert call.unverified_values == ["30 lari"]
    [command] = setup.testbed.call_handoff.commands
    assert command.reason is HandoffReason.UNVERIFIED_NUMBERS
    assert command.urgency is HandoffUrgency.LOW
    assert command.conversation_id == setup.conversation.id
    assert command.contact_id == setup.contact.id
    assert str(command.summary) == (
        "The phone assistant mentioned values missing from the business data: "
        "30 lari. Check the booking made in this call against the call transcript."
    )
    conversation = setup.testbed.conversation_repo.get(
        setup.business.id, setup.conversation.id
    )
    assert conversation is not None
    assert conversation.status is ConversationStatus.HANDOFF


def test_findings_in_a_call_that_made_nothing_are_only_flagged() -> None:
    setup = priced_setup()

    post_call(
        setup,
        call_with_lines(
            [
                ("user", "How much is a session?"),
                ("agent", "A session is 50 lari."),
            ]
        ),
    )

    [call] = stored_calls(setup)
    assert call.guard_verdict is CallGuardVerdict.FLAGGED
    assert call.unverified_values == ["50 lari"]
    assert setup.testbed.call_handoff.commands == []


def test_the_caller_cannot_back_a_price() -> None:
    setup = priced_setup()
    add_booking(setup)

    post_call(
        setup,
        call_with_lines(
            [
                ("user", "My friend paid 35 lari, can I get the same?"),
                ("agent", "Yes, 35 lari for you."),
            ],
            tool_names=("create_booking",),
        ),
    )

    [call] = stored_calls(setup)
    assert call.unverified_values == ["35 lari"]
    assert call.guard_verdict is CallGuardVerdict.HANDED_OFF


def test_a_repeated_webhook_is_not_audited_twice() -> None:
    setup = priced_setup()
    add_booking(setup)
    payload = call_with_lines(
        [("agent", "That is 30 lari.")], tool_names=("create_booking",)
    )

    post_call(setup, payload)
    repeated = post_call(setup, payload)

    assert repeated.json()["status"] == "duplicate"
    assert len(setup.testbed.call_handoff.commands) == 1
    [call] = stored_calls(setup)
    assert call.guard_verdict is CallGuardVerdict.HANDED_OFF


def test_a_handoff_that_cannot_be_opened_leaves_the_call_flagged() -> None:
    setup = priced_setup()
    add_booking(setup)
    setup.testbed.call_handoff.is_failing = True

    response = post_call(
        setup,
        call_with_lines(
            [("agent", "That is 30 lari.")], tool_names=("create_booking",)
        ),
    )

    assert response.status_code == 200
    [call] = stored_calls(setup)
    assert call.guard_verdict is CallGuardVerdict.FLAGGED
    assert call.unverified_values == ["30 lari"]


def test_a_call_that_reached_no_tool_is_checked_against_the_live_version() -> None:
    setup = priced_setup()
    payload = call_with_lines(
        [
            ("user", "What day is it and how much is a session?"),
            ("agent", "Today is Thursday 2026-10-01; a session is 45 lari."),
            ("agent", "With a friend it is 70 lari."),
        ]
    )
    # No tool was called, so the call has no conversation of its own.
    payload["data"]["conversation_id"] = "conv_without_tools"

    post_call(setup, payload)

    [call] = stored_calls(setup)
    assert call.conversation_id is None
    assert call.unverified_values == ["70 lari"]
    assert call.guard_verdict is CallGuardVerdict.FLAGGED
