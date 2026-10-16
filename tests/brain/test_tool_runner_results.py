"""Tool results: prices in major units, search language and every tool end to end."""

from typing import Any

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from tests.brain.brain_world import build_world
from tests.brain.scripted_turns import scripted
from tests.brain.tool_runner_helpers import BOOKING_ARGUMENTS, run_tool


def test_prices_are_rendered_in_major_units_of_their_currency() -> None:
    world = build_world(scripted())

    found, _ = run_tool(world, AssistantToolName.GET_PRICE, {"item_name": "khachapuri"})
    missing, _ = run_tool(world, AssistantToolName.GET_PRICE, {"item_name": "sushi"})

    assert found["found"] is True
    assert found["matches"][0]["price"] == "18.00"
    assert found["matches"][0]["currency"] == "GEL"
    assert found["matches"][0]["price_text"] == "18,00 ₾"
    assert missing == {
        "found": False,
        "note": "Not in the price list: do not name any price.",
        "matches": [],
    }


def test_search_language_defaults_to_the_conversation_language() -> None:
    world = build_world(scripted())

    run_tool(
        world,
        AssistantToolName.SEARCH_KNOWLEDGE,
        {"query": "khinkali", "language": None},
    )
    run_tool(
        world,
        AssistantToolName.SEARCH_KNOWLEDGE,
        {"query": "khinkali", "language": "pt-BR"},
    )

    assert [str(request.language) for request in world.search_knowledge.requests] == [
        "ka",
        "pt-BR",
    ]


def test_every_tool_runs_end_to_end_with_the_fakes() -> None:
    world = build_world(scripted())
    created, _ = run_tool(world, AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS)
    calls: dict[AssistantToolName, dict[str, Any]] = {
        AssistantToolName.SEARCH_KNOWLEDGE: {"query": "khinkali", "language": None},
        AssistantToolName.CHECK_AVAILABILITY: {
            "resource_type": None,
            "date": "2026-10-02",
            "time": None,
            "party_size": 2,
            "duration_minutes": None,
            "nights": None,
        },
        AssistantToolName.RESCHEDULE_BOOKING: {
            "booking_id": created["booking_id"],
            "phone": None,
            "old_date": None,
            "new_date": "2026-10-03",
            "new_time": "20:00",
        },
        AssistantToolName.CANCEL_BOOKING: {
            "booking_id": created["booking_id"],
            "phone": None,
            "date": None,
        },
        AssistantToolName.CREATE_LEAD: {
            "lead_type": "banquet",
            "details": "Wedding for 80 guests",
            "name": None,
            "phone": None,
            "requested_date": "2026-11-14",
            "party_size": 80,
            "budget": None,
        },
        AssistantToolName.SEND_LINK: {"kind": "menu"},
        AssistantToolName.RECORD_UNANSWERED_QUESTION: {"question": "Is there parking?"},
    }

    results = {
        tool_name: run_tool(world, tool_name, arguments)
        for tool_name, arguments in calls.items()
    }

    assert all(not is_error for _, is_error in results.values())
    assert results[AssistantToolName.CHECK_AVAILABILITY][0]["slots"][0]["time"] == (
        "19:30"
    )
    assert results[AssistantToolName.RESCHEDULE_BOOKING][0]["date"] == "2026-10-03"
    assert results[AssistantToolName.CANCEL_BOOKING][0]["status"] == "cancelled"
    assert results[AssistantToolName.CREATE_LEAD][0]["lead_type"] == "banquet"
    assert results[AssistantToolName.SEND_LINK][0]["url"] == (
        "https://sakhli.example/menu"
    )
    assert results[AssistantToolName.RECORD_UNANSWERED_QUESTION][0]["recorded"] is True
    no_link, _ = run_tool(world, AssistantToolName.SEND_LINK, {"kind": "payment"})
    assert no_link["url"] is None
    assert world.create_lead.commands[0].contact_phone_number == "+995577000111"
    assert world.record_question.commands[0].language == LanguageTag("ka")
    assert world.business.country_code == CountryCode("GE")
