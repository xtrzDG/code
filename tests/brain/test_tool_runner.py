import json
from typing import Any, cast

import pytest

from app.registries.tools.assistant_tool_registry import AssistantToolRegistry
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolInvocation,
    CancelBookingToolInput,
    CheckAvailabilityToolInput,
    CreateBookingToolInput,
    CreateLeadToolInput,
    GetPriceToolInput,
    HandoffToHumanToolInput,
    RecordUnansweredQuestionToolInput,
    RescheduleBookingToolInput,
    SearchKnowledgeToolInput,
    SendLinkToolInput,
)
from app.schemas.dto.bookings import (
    CancelBookingCommand,
    CreateBookingCommand,
    RescheduleBookingCommand,
)
from app.schemas.dto.conversations import LlmToolCall
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import LlmToolCallId, LlmToolInputJson
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.business_setups import ISRAEL
from tests.brain.scripted_turns import scripted

INPUT_MODELS: dict[AssistantToolName, type[Any]] = {
    AssistantToolName.SEARCH_KNOWLEDGE: SearchKnowledgeToolInput,
    AssistantToolName.GET_PRICE: GetPriceToolInput,
    AssistantToolName.CHECK_AVAILABILITY: CheckAvailabilityToolInput,
    AssistantToolName.CREATE_BOOKING: CreateBookingToolInput,
    AssistantToolName.CANCEL_BOOKING: CancelBookingToolInput,
    AssistantToolName.RESCHEDULE_BOOKING: RescheduleBookingToolInput,
    AssistantToolName.CREATE_LEAD: CreateLeadToolInput,
    AssistantToolName.HANDOFF_TO_HUMAN: HandoffToHumanToolInput,
    AssistantToolName.SEND_LINK: SendLinkToolInput,
    AssistantToolName.RECORD_UNANSWERED_QUESTION: RecordUnansweredQuestionToolInput,
}
SERVER_SIDE_FIELDS: set[str] = {
    "business_id",
    "contact_id",
    "conversation_id",
    "channel",
    "source_channel",
    "is_sandbox",
}


def walk_schemas(schema: dict[str, Any]) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = [schema]
    for value in schema.values():
        children: list[object] = (
            cast(list[object], value) if isinstance(value, list) else [value]
        )
        for child in children:
            if isinstance(child, dict):
                schemas.extend(walk_schemas(cast(dict[str, Any], child)))

    return schemas


@pytest.mark.parametrize("tool_name", list(AssistantToolName))
def test_every_tool_has_a_strict_schema_matching_its_input_dto(
    tool_name: AssistantToolName,
) -> None:
    definition = AssistantToolRegistry().get(tool_name)
    schema: dict[str, Any] = json.loads(definition.input_schema_json)

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["required"] == list(schema["properties"])
    assert set(schema["properties"]) == set(INPUT_MODELS[tool_name].model_fields)
    assert not set(schema["properties"]) & SERVER_SIDE_FIELDS
    for nested in walk_schemas(schema):
        assert not {"minimum", "maximum", "pattern", "format"} & set(nested)

    assert str(definition.description) != ""


def test_definitions_are_deterministic_and_deduplicated() -> None:
    first, second = AssistantToolRegistry(), AssistantToolRegistry()
    names = [AssistantToolName.GET_PRICE, AssistantToolName.SEND_LINK]

    assert first.list_definitions(names) == second.list_definitions(names)
    assert [
        definition.name
        for definition in first.list_definitions([*names, AssistantToolName.GET_PRICE])
    ] == names


def test_the_engine_only_reason_is_not_offered_to_the_model() -> None:
    schema = json.loads(
        AssistantToolRegistry()
        .get(AssistantToolName.HANDOFF_TO_HUMAN)
        .input_schema_json
    )

    assert "unverified_numbers" not in schema["properties"]["reason"]["enum"]
    assert "customer_request" in schema["properties"]["reason"]["enum"]


def build_context(world: BrainWorld, **changes: Any) -> AssistantToolContext:
    context = AssistantToolContext(
        business_id=world.business.id,
        business_country_code=world.business.country_code,
        contact_id=ContactId(),
        contact_phone_number=E164PhoneNumber("+995577000111"),
        conversation_id=ConversationId(),
        channel=ChannelKind.TELEGRAM,
        language=LanguageTag("ka"),
        available_tools=list(AssistantToolName),
    )
    return context.model_copy(update=changes)


def run_tool(
    world: BrainWorld,
    tool_name: AssistantToolName,
    arguments: dict[str, Any] | str,
    context: AssistantToolContext | None = None,
) -> tuple[dict[str, Any], bool]:
    outcome = world.run_tool.run(
        AssistantToolInvocation(
            context=context if context is not None else build_context(world),
            call=LlmToolCall(
                call_id=LlmToolCallId("call_1"),
                tool_name=tool_name,
                input_json=LlmToolInputJson(
                    arguments
                    if isinstance(arguments, str)
                    else json.dumps(arguments, ensure_ascii=False)
                ),
            ),
        )
    )
    assert outcome.result.call_id == "call_1"
    return json.loads(outcome.result.result_json), outcome.result.is_error


BOOKING_ARGUMENTS: dict[str, Any] = {
    "name": "Nino",
    "phone": None,
    "resource_type": "table",
    "date": "2026-10-02",
    "time": "19:30",
    "party_size": 4,
    "duration_minutes": None,
    "nights": None,
    "notes": "window seat",
}


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
    ("setup_is_israel", "raw_phone", "expected"),
    [
        (False, "555 12 34 56", "+995555123456"),
        (False, "+995 555-12-34-56", "+995555123456"),
        (False, "+49 30 901820", "+4930901820"),
        (True, "054-723-4567", "+972547234567"),
        (True, "+972 52 555 1234", "+972525551234"),
    ],
)
def test_model_phones_are_parsed_with_the_business_country(
    setup_is_israel: bool,
    raw_phone: str,
    expected: str,
) -> None:
    world = (
        build_world(scripted(), ISRAEL) if setup_is_israel else build_world(scripted())
    )

    _, is_error = run_tool(
        world,
        AssistantToolName.CREATE_BOOKING,
        BOOKING_ARGUMENTS | {"phone": raw_phone},
        build_context(world, business_country_code=world.business.country_code),
    )

    assert is_error is False
    command = world.bookings.commands[0]
    assert isinstance(command, CreateBookingCommand)
    assert command.contact_phone_number == expected


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


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        (
            AssistantToolName.CANCEL_BOOKING,
            {"booking_id": None, "phone": "+995599765432", "date": "2026-10-06"},
        ),
        (
            AssistantToolName.RESCHEDULE_BOOKING,
            {
                "booking_id": None,
                "phone": "+995 599 76 54 32",
                "old_date": "2026-10-06",
                "new_date": "2026-10-07",
                "new_time": "20:00",
            },
        ),
    ],
)
def test_a_typed_phone_never_proves_whose_booking_it_is(
    tool_name: AssistantToolName,
    arguments: dict[str, Any],
) -> None:
    world = build_world(scripted())
    stranger = build_context(
        world, contact_phone_number=E164PhoneNumber("+995599765432")
    )

    result, is_error = run_tool(world, tool_name, arguments, stranger)

    assert is_error is True
    assert "not confirmed" in result["error"]
    assert world.bookings.commands == []


def test_bookings_are_found_by_the_phone_the_channel_proved() -> None:
    world = build_world(scripted())
    whatsapp = build_context(
        world,
        channel=ChannelKind.WHATSAPP,
        verified_phone_number=E164PhoneNumber("+995577000111"),
        is_sandbox=True,
    )

    run_tool(
        world,
        AssistantToolName.CANCEL_BOOKING,
        {"booking_id": None, "phone": "577 00 01 11", "date": "2026-10-02"},
        whatsapp,
    )
    run_tool(
        world,
        AssistantToolName.RESCHEDULE_BOOKING,
        {
            "booking_id": None,
            "phone": None,
            "old_date": "2026-10-02",
            "new_date": "2026-10-03",
            "new_time": None,
        },
        build_context(world),
    )

    cancel_command, reschedule_command = world.bookings.commands
    assert isinstance(cancel_command, CancelBookingCommand)
    assert isinstance(reschedule_command, RescheduleBookingCommand)
    assert cancel_command.contact_phone_number == "+995577000111"
    assert cancel_command.is_sandbox is True
    # Without a proved phone only the conversation's own contact counts.
    assert reschedule_command.contact_phone_number is None
    assert reschedule_command.is_sandbox is False


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
