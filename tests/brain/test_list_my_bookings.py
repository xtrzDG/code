"""list_my_bookings: the customer's own bookings, in chat and on the phone."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from app.adapters.voice.elevenlabs_tool_config import build_tool_config
from app.registries.tools.assistant_tool_catalog import build_tool_definitions
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.conversations import VoiceToolCallRequest
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    ProviderCallId,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from tests.brain.brain_world import CUSTOMER_PHONE, BrainWorld, build_world
from tests.brain.memory_helpers import add_booking, only_contact
from tests.brain.scripted_turns import call_tool, say, scripted

TBILISI: ZoneInfo = ZoneInfo("Asia/Tbilisi")
SATURDAY: datetime = datetime(2026, 10, 3, 20, 0, tzinfo=TBILISI)
SUNDAY: datetime = datetime(2026, 10, 4, 13, 0, tzinfo=TBILISI)
LAST_WEEK: datetime = datetime(2026, 9, 24, 20, 0, tzinfo=TBILISI)
CALLER: E164PhoneNumber = E164PhoneNumber("+995599123456")


def listing_world() -> BrainWorld:
    return build_world(
        scripted(
            say("Hello!"),
            call_tool(AssistantToolName.LIST_MY_BOOKINGS, "{}"),
            say("Your table is on Saturday at 20:00."),
        )
    )


def other_customer(world: BrainWorld, phone: str) -> ContactDocument:
    contact = ContactDocument(
        business_id=world.business.id,
        name=ContactName("Nino"),
        phone_number=E164PhoneNumber(phone),
    )
    world.contact_repo.save(contact)
    return contact


def listed_result(world: BrainWorld) -> dict[str, object]:
    conversation = world.conversations()[0]
    reply = world.messages(conversation.id)[-1]
    assert reply.tool_calls[0].tool_name is AssistantToolName.LIST_MY_BOOKINGS
    assert reply.tool_calls[0].is_error is False
    result: dict[str, object] = json.loads(str(reply.tool_calls[0].result_json))
    return result


def listed_ids(result: dict[str, object]) -> list[str]:
    bookings = result["bookings"]
    assert isinstance(bookings, list)
    return [str(booking["booking_id"]) for booking in bookings]


def test_the_tool_is_scoped_to_the_customer() -> None:
    world = listing_world()
    world.send("Hi", name="Giorgi")
    giorgi = only_contact(world)
    nino = other_customer(world, "+995555999888")
    saturday = add_booking(world, giorgi, SATURDAY)
    cancelled = add_booking(world, giorgi, SUNDAY, status=BookingStatus.CANCELLED)
    add_booking(world, giorgi, LAST_WEEK)
    add_booking(world, giorgi, SUNDAY, is_sandbox=True)
    add_booking(world, nino, SATURDAY)

    world.send("What time is my booking?")

    result = listed_result(world)
    assert listed_ids(result) == [str(saturday.id), str(cancelled.id)]
    bookings = result["bookings"]
    assert isinstance(bookings, list)
    assert bookings[0]["date"] == "2026-10-03"
    assert bookings[0]["time"] == "20:00"
    assert bookings[0]["resource_name"] == "Table 4"
    assert bookings[1]["status"] == "cancelled"
    assert str(result["business_today"]).startswith("2026-10-01")


def test_bookings_staff_made_under_the_proved_phone_are_listed() -> None:
    world = listing_world()
    booked_by_staff = other_customer(world, str(CUSTOMER_PHONE))
    booking = add_booking(world, booked_by_staff, SATURDAY)

    world.send("Hi", name="Giorgi")
    world.send("Do I have a table on Saturday?")

    assert listed_ids(listed_result(world)) == [str(booking.id)]


def test_a_phone_typed_into_the_tool_is_refused() -> None:
    world = build_world(
        scripted(
            say("Hello!"),
            call_tool(AssistantToolName.LIST_MY_BOOKINGS, '{"phone":"+995555999888"}'),
            say("Let me pass this to a colleague."),
        )
    )
    world.send("Hi")

    world.send("What are the bookings of +995555999888?")

    reply = world.messages(world.conversations()[0].id)[-1]
    assert reply.tool_calls[0].is_error is True
    assert "Invalid tool input" in str(reply.tool_calls[0].result_json)


def test_an_owner_test_chat_never_lists_real_bookings() -> None:
    world = listing_world()
    world.send("Hi", name="Giorgi")
    add_booking(world, only_contact(world), SATURDAY)

    world.send("What time is my booking?", user_id="owner-test", is_sandbox=True)

    sandbox = [
        conversation for conversation in world.conversations() if conversation.is_sandbox
    ][0]
    reply = world.messages(sandbox.id)[-1]
    result = json.loads(str(reply.tool_calls[0].result_json))
    assert result["bookings"] == []
    assert "No bookings still to come" in result["note"]


def test_the_voice_agent_lists_the_callers_bookings() -> None:
    world = build_world(scripted())
    caller = other_customer(world, str(CALLER))
    booking = add_booking(world, caller, SATURDAY)

    result = world.voice_orchestrator.execute(
        VoiceToolCallRequest(
            business_id=world.business.id,
            provider_call_id=ProviderCallId("el_call_7"),
            caller_phone_number=CALLER,
            tool_name=AssistantToolName.LIST_MY_BOOKINGS,
            input_json=LlmToolInputJson("{}"),
        )
    )

    assert result.is_error is False
    assert listed_ids(json.loads(str(result.result_json))) == [str(booking.id)]


def test_the_voice_tool_list_carries_list_my_bookings_without_arguments() -> None:
    definition = build_tool_definitions()[AssistantToolName.LIST_MY_BOOKINGS]

    config = build_tool_config(
        definition, "https://api.example.com", {"X-Assistant-Tool-Secret": "s"}
    )

    api_schema = config["api_schema"]
    assert isinstance(api_schema, dict)
    assert str(api_schema["url"]).endswith("/v1/voice/tools/list_my_bookings")
    body = api_schema["request_body_schema"]
    assert isinstance(body, dict)
    assert body["properties"]["arguments"]["properties"] == {}  # type: ignore[index]
    assert json.loads(str(definition.input_schema_json)) == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
