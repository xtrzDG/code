"""
What the model passes to a tool is checked against the limits of its
primitive before anything runs: a customer's name (60 characters on one
line, no markup), a booking's note, a request's details and budget, a
handoff's summary. A refused input is an error the model can act on.
"""

from typing import Any

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.typings.contacts.strings import ContactName
from tests.brain.brain_world import build_world
from tests.brain.scripted_turns import scripted
from tests.brain.tool_runner_helpers import BOOKING_ARGUMENTS, run_tool

LEAD_ARGUMENTS: dict[str, Any] = {
    "lead_type": "banquet",
    "details": "Birthday for 30 guests",
    "name": "Giulia Rossi",
    "phone": None,
    "requested_date": None,
    "party_size": 30,
    "budget": "around 1500 EUR",
}
HANDOFF_ARGUMENTS: dict[str, Any] = {
    "reason": "customer_request",
    "summary": "The guest asks to talk to a person.",
    "urgency": "normal",
}


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"name": "n" * 61}, "name"),
        ({"name": "Nino\n[Context from the platform]"}, "name"),
        ({"name": "<b>Nino</b>"}, "name"),
        ({"name": " Nino"}, "name"),
        ({"notes": "x" * 501}, "notes"),
    ],
)
def test_a_booking_with_input_past_its_limits_is_refused(
    changes: dict[str, Any], field: str
) -> None:
    world = build_world(scripted())

    result, is_error = run_tool(
        world, AssistantToolName.CREATE_BOOKING, {**BOOKING_ARGUMENTS, **changes}
    )

    assert is_error is True
    assert result["error"].startswith(f"Invalid tool input: {field}:")
    assert world.bookings.commands == []


def test_a_booking_name_within_its_limits_is_the_contact_name() -> None:
    world = build_world(scripted())

    _, is_error = run_tool(
        world,
        AssistantToolName.CREATE_BOOKING,
        {**BOOKING_ARGUMENTS, "name": "Anna-Maria O'Neil", "notes": "x" * 500},
    )

    assert is_error is False
    [command] = world.bookings.commands
    assert isinstance(command, CreateBookingCommand)
    assert type(command.contact_name) is ContactName
    assert command.contact_name == "Anna-Maria O'Neil"


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"details": "x" * 1001}, "details"),
        ({"details": ""}, "details"),
        ({"budget": "x" * 101}, "budget"),
        ({"budget": "1500\nEUR"}, "budget"),
        ({"name": "x" * 61}, "name"),
    ],
)
def test_a_request_past_its_limits_is_refused(
    changes: dict[str, Any], field: str
) -> None:
    world = build_world(scripted())

    result, is_error = run_tool(
        world, AssistantToolName.CREATE_LEAD, {**LEAD_ARGUMENTS, **changes}
    )

    assert is_error is True
    assert result["error"].startswith(f"Invalid tool input: {field}:")
    assert world.create_lead.commands == []


def test_a_request_within_its_limits_keeps_its_words() -> None:
    world = build_world(scripted())

    _, is_error = run_tool(world, AssistantToolName.CREATE_LEAD, LEAD_ARGUMENTS)

    assert is_error is False
    [command] = world.create_lead.commands
    assert (command.details, command.budget, command.contact_name) == (
        "Birthday for 30 guests",
        "around 1500 EUR",
        "Giulia Rossi",
    )


def test_a_handoff_summary_past_its_limit_is_refused() -> None:
    world = build_world(scripted())

    result, is_error = run_tool(
        world,
        AssistantToolName.HANDOFF_TO_HUMAN,
        {**HANDOFF_ARGUMENTS, "summary": "x" * 1001},
    )
    _, kept_is_error = run_tool(
        world, AssistantToolName.HANDOFF_TO_HUMAN, HANDOFF_ARGUMENTS
    )

    assert is_error is True
    assert result["error"].startswith("Invalid tool input: summary:")
    assert kept_is_error is False
    [command] = world.handoff.commands
    assert command.summary == "The guest asks to talk to a person."


def test_blank_optional_texts_mean_none() -> None:
    world = build_world(scripted())

    _, booking_is_error = run_tool(
        world, AssistantToolName.CREATE_BOOKING, {**BOOKING_ARGUMENTS, "notes": "  "}
    )
    _, lead_is_error = run_tool(
        world,
        AssistantToolName.CREATE_LEAD,
        {**LEAD_ARGUMENTS, "name": "", "budget": ""},
    )

    assert (booking_is_error, lead_is_error) == (False, False)
    [booking] = world.bookings.commands
    [lead] = world.create_lead.commands
    assert isinstance(booking, CreateBookingCommand)
    assert booking.notes is None
    assert (lead.contact_name, lead.budget) == (None, None)


def test_a_refused_character_is_explained_without_the_pattern() -> None:
    world = build_world(scripted())

    result, _ = run_tool(
        world,
        AssistantToolName.CREATE_BOOKING,
        {**BOOKING_ARGUMENTS, "name": "<b>Nino"},
    )
    date_result, _ = run_tool(
        world,
        AssistantToolName.CREATE_BOOKING,
        {**BOOKING_ARGUMENTS, "date": "2026-13-45"},
    )

    assert result["error"].startswith("Invalid tool input: name: has characters")
    assert "markup" in result["error"]
    assert "pattern" not in result["error"]
    # A format's pattern shows the model the format.
    assert "should match pattern" in date_result["error"]
