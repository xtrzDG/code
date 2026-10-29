"""Scheduling tools state today at the business and refuse dates that have passed."""

from typing import Any

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.localization.constrained_strings import TimezoneName
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import scripted
from tests.brain.tool_runner_helpers import BOOKING_ARGUMENTS, build_context, run_tool

# The world's clock: Thursday 2026-10-01 14:00 in Tbilisi.
TODAY: str = "2026-10-01 (Thursday)"


def run_in_tbilisi(
    world: BrainWorld,
    tool_name: AssistantToolName,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    return run_tool(
        world,
        tool_name,
        arguments,
        build_context(world, business_timezone=TimezoneName("Asia/Tbilisi")),
    )


def availability(date: str) -> dict[str, Any]:
    return {
        "resource_type": None,
        "date": date,
        "time": None,
        "party_size": 2,
        "duration_minutes": None,
        "nights": None,
    }


def test_availability_and_bookings_state_today_at_the_business() -> None:
    world = build_world(scripted())

    slots, slots_error = run_in_tbilisi(
        world, AssistantToolName.CHECK_AVAILABILITY, availability("2026-10-02")
    )
    booking, booking_error = run_in_tbilisi(
        world, AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS
    )

    assert (slots_error, booking_error) == (False, False)
    assert slots["business_today"] == TODAY
    assert booking["business_today"] == TODAY
    assert booking["date"] == "2026-10-02"


def test_today_follows_the_business_time_zone() -> None:
    world = build_world(scripted())
    context = build_context(world, business_timezone=TimezoneName("Pacific/Kiritimati"))

    result, _ = run_tool(
        world,
        AssistantToolName.CHECK_AVAILABILITY,
        availability("2026-10-03"),
        context,
    )

    # 14:00 in Tbilisi is already the next morning on Kiritimati (UTC+14).
    assert result["business_today"] == "2026-10-02 (Friday)"


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        (AssistantToolName.CHECK_AVAILABILITY, availability("2026-09-30")),
        (AssistantToolName.CREATE_BOOKING, {**BOOKING_ARGUMENTS, "date": "2025-10-02"}),
        (
            AssistantToolName.RESCHEDULE_BOOKING,
            {
                "booking_id": None,
                "phone": None,
                "old_date": "2026-10-02",
                "new_date": "2026-09-29",
                "new_time": "20:00",
            },
        ),
    ],
)
def test_a_date_that_has_passed_is_refused_with_today(
    tool_name: AssistantToolName,
    arguments: dict[str, Any],
) -> None:
    world = build_world(scripted())

    result, is_error = run_in_tbilisi(world, tool_name, arguments)

    assert is_error is True
    assert result["business_today"] == TODAY
    assert (
        "has already passed: today at the business is 2026-10-01" in (result["error"])
    )
    assert world.availability.queries == []
    assert world.bookings.commands == []


def test_today_itself_is_not_in_the_past() -> None:
    world = build_world(scripted())

    result, is_error = run_in_tbilisi(
        world, AssistantToolName.CHECK_AVAILABILITY, availability("2026-10-01")
    )

    assert is_error is False
    assert result["business_today"] == TODAY


def test_errors_of_scheduling_tools_carry_today_and_others_do_not() -> None:
    world = build_world(scripted())
    world.bookings.is_slot_taken = True

    taken, taken_error = run_in_tbilisi(
        world, AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS
    )
    invalid, invalid_error = run_in_tbilisi(
        world, AssistantToolName.CHECK_AVAILABILITY, {"date": "tomorrow"}
    )
    price, price_error = run_in_tbilisi(world, AssistantToolName.GET_PRICE, {})

    assert (taken_error, invalid_error, price_error) == (True, True, True)
    assert taken["business_today"] == TODAY
    assert "already taken" in taken["error"]
    assert invalid["business_today"] == TODAY
    assert "business_today" not in price


def test_without_a_known_time_zone_nothing_is_added() -> None:
    world = build_world(scripted())

    result, is_error = run_tool(
        world, AssistantToolName.CHECK_AVAILABILITY, availability("2026-09-30")
    )

    assert is_error is False
    assert "business_today" not in result
