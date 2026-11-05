"""
The tool runner's input checks: server-side context, bad input, refused tools, errors.
"""

from typing import Any

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.bookings import CreateBookingCommand
from tests.brain.brain_world import build_world
from tests.brain.scripted_turns import scripted
from tests.brain.tool_runner_helpers import BOOKING_ARGUMENTS, build_context, run_tool


def test_booking_runs_with_server_side_context_and_contact_phone_fallback() -> None:
    world = build_world(scripted())
    context = build_context(world)

    result, is_error = run_tool(
        world, AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS, context
    )

    assert is_error is False
    command = world.bookings.commands[0]
    assert isinstance(command, CreateBookingCommand)
    assert command.business_id == context.business_id
    assert command.contact_id == context.contact_id
    assert command.conversation_id == context.conversation_id
    assert command.source_channel is ChannelKind.TELEGRAM
    assert command.language == "ka"
    assert command.contact_phone_number == "+995577000111"
    assert result["time"] == "19:30"
    assert result["party_size"] == 4
    assert result["booking_id"].startswith("booking_")


@pytest.mark.parametrize(
    ("arguments", "message_part"),
    [
        (BOOKING_ARGUMENTS | {"phone": "12"}, "not a valid phone"),
        (BOOKING_ARGUMENTS | {"date": "tomorrow"}, "date"),
        (BOOKING_ARGUMENTS | {"party_size": 0}, "party_size"),
        (BOOKING_ARGUMENTS | {"business_id": "business_x"}, "business_id"),
        ("{not json", "Invalid tool input"),
    ],
)
def test_bad_model_input_becomes_an_error_result(
    arguments: dict[str, Any] | str,
    message_part: str,
) -> None:
    world = build_world(scripted())

    result, is_error = run_tool(world, AssistantToolName.CREATE_BOOKING, arguments)

    assert is_error is True
    assert message_part in result["error"]
    assert world.bookings.bookings == {}


def test_business_rule_errors_become_error_results() -> None:
    world = build_world(scripted())
    world.bookings.is_slot_taken = True

    result, is_error = run_tool(
        world, AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS
    )
    cancel_result, cancel_is_error = run_tool(
        world,
        AssistantToolName.CANCEL_BOOKING,
        {"booking_id": None, "phone": None, "date": "2026-10-02"},
    )

    assert is_error is True
    assert "already taken" in result["error"]
    assert cancel_is_error is True
    assert "No booking" in cancel_result["error"]


def test_tools_not_offered_in_the_conversation_are_refused() -> None:
    world = build_world(scripted())
    context = build_context(world, available_tools=[AssistantToolName.CREATE_LEAD])

    result, is_error = run_tool(
        world, AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS, context
    )

    assert is_error is True
    assert "not available" in result["error"]
    assert world.bookings.commands == []


def test_far_away_dates_are_refused_as_input() -> None:
    world = build_world(scripted())

    result, is_error = run_tool(
        world,
        AssistantToolName.CHECK_AVAILABILITY,
        {
            "resource_type": None,
            "date": "0001-01-01",
            "time": None,
            "party_size": 2,
            "duration_minutes": None,
            "nights": None,
        },
    )

    assert is_error is True
    assert "date" in result["error"]


def test_an_unexpected_tool_failure_becomes_an_error_result() -> None:
    world = build_world(scripted())

    def explode(_: object) -> object:
        raise OverflowError("date value out of range")

    world.availability.run = explode  # type: ignore[method-assign,assignment]

    result, is_error = run_tool(
        world,
        AssistantToolName.CHECK_AVAILABILITY,
        {
            "resource_type": None,
            "date": "2026-10-02",
            "time": None,
            "party_size": 2,
            "duration_minutes": None,
            "nights": None,
        },
    )

    assert is_error is True
    assert "colleague" in result["error"]
