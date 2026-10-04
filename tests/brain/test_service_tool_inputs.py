"""The model names services, masters and stays; the tools pass them on as written."""

import json
from typing import Any

from app.registries.tools.assistant_tool_registry import AssistantToolRegistry
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.bookings import CreateBookingCommand
from tests.brain.brain_world import build_world
from tests.brain.scripted_turns import scripted
from tests.brain.tool_runner_helpers import BOOKING_ARGUMENTS, run_tool

AVAILABILITY_ARGUMENTS: dict[str, Any] = {
    "service_id": None,
    "resource_id": None,
    "resource_type": None,
    "date": "2026-10-02",
    "time": "12:00",
    "party_size": 1,
    "duration_minutes": None,
    "nights": None,
}


def test_availability_gets_the_service_and_the_master_as_the_customer_wrote() -> None:
    world = build_world(scripted())

    _, is_error = run_tool(
        world,
        AssistantToolName.CHECK_AVAILABILITY,
        AVAILABILITY_ARGUMENTS | {"service_id": "стрижку", "resource_id": "ნინო"},
    )

    assert is_error is False
    query = world.availability.queries[0]
    assert (query.service_reference, query.resource_reference) == ("стрижку", "ნინო")
    assert (query.resource_id, query.service_item_id) == (None, None)


def test_booking_gets_the_service_id_and_the_master() -> None:
    world = build_world(scripted())
    service_id = "knowledge_item_0b6f1c1e-0000-4000-8000-000000000045"

    _, is_error = run_tool(
        world,
        AssistantToolName.CREATE_BOOKING,
        BOOKING_ARGUMENTS
        | {"service_id": service_id, "resource_id": "Nino", "resource_type": None},
    )

    assert is_error is False
    command = world.bookings.commands[0]
    assert isinstance(command, CreateBookingCommand)
    assert (command.service_reference, command.resource_reference) == (
        service_id,
        "Nino",
    )
    assert command.resource_id is None


def test_get_price_gets_the_stay_to_quote() -> None:
    world = build_world(scripted())

    _, is_error = run_tool(
        world,
        AssistantToolName.GET_PRICE,
        {"item_name": "Deluxe room", "check_in_date": "2027-08-10", "nights": 3},
    )

    assert is_error is False
    query = world.get_price.queries[0]
    assert (query.item_name, query.check_in, query.nights) == (
        "Deluxe room",
        "2027-08-10",
        3,
    )


def test_a_bad_check_in_date_is_an_error_result() -> None:
    world = build_world(scripted())

    result, is_error = run_tool(
        world,
        AssistantToolName.GET_PRICE,
        {"item_name": "Deluxe room", "check_in_date": "in August", "nights": 3},
    )

    assert is_error is True
    assert "check_in_date" in result["error"]
    assert world.get_price.queries == []


def test_the_tool_definitions_explain_services_and_masters() -> None:
    registry = AssistantToolRegistry()
    for tool_name in (
        AssistantToolName.CHECK_AVAILABILITY,
        AssistantToolName.CREATE_BOOKING,
    ):
        properties = json.loads(registry.get(tool_name).input_schema_json)[
            "properties"
        ]
        assert "its id" in properties["service_id"]["description"]
        assert "any script" in properties["resource_id"]["description"]

    price = json.loads(registry.get(AssistantToolName.GET_PRICE).input_schema_json)
    assert {"check_in_date", "nights"} <= set(price["properties"])
