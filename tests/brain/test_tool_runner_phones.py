"""
Phones in tool calls: parsed with the business country, proven only by the channel.
"""

import json
from typing import Any

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.bookings import (
    CancelBookingCommand,
    CreateBookingCommand,
    RescheduleBookingCommand,
)
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from tests.brain.brain_world import build_world
from tests.brain.business_setups import ISRAEL
from tests.brain.scripted_turns import call_tool, say, scripted
from tests.brain.tool_runner_helpers import BOOKING_ARGUMENTS, build_context, run_tool


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
    # The channel the request came from: a phone call's request is refused
    # by the booking use cases (a caller id proves nobody).
    assert cancel_command.source_channel is ChannelKind.WHATSAPP
    assert reschedule_command.source_channel is ChannelKind.TELEGRAM


def test_a_booking_carries_the_website_visitors_network() -> None:
    world = build_world(scripted())
    web_chat = build_context(
        world,
        channel=ChannelKind.WEB_CHAT,
        client_ip_address=ClientIpAddress("203.0.113.7"),
    )

    run_tool(world, AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS, web_chat)
    run_tool(world, AssistantToolName.CREATE_BOOKING, BOOKING_ARGUMENTS)

    from_web, from_telegram = world.bookings.commands
    assert isinstance(from_web, CreateBookingCommand)
    assert isinstance(from_telegram, CreateBookingCommand)
    # Anonymous bookings are capped per client network (booking_limits).
    assert from_web.client_ip_address == "203.0.113.7"
    assert from_telegram.client_ip_address is None


def test_a_web_chat_turn_hands_the_visitors_network_to_the_booking() -> None:
    # The inbox's message carries the address (widget, hosted chat); the
    # turn's tool context passes it on, so the per-network cap applies.
    world = build_world(
        scripted(
            call_tool(AssistantToolName.CREATE_BOOKING, json.dumps(BOOKING_ARGUMENTS)),
            say("Booked."),
        )
    )

    world.pipeline.start(
        InboundMessage(
            business_id=world.business.id,
            channel=ChannelKind.WEB_CHAT,
            channel_user_id=ChannelUserId("widget-session-1"),
            text=MessageText("A table for four tomorrow at 19:30, please"),
            client_ip_address=ClientIpAddress("198.51.100.4"),
        )
    )

    [command] = world.bookings.commands
    assert isinstance(command, CreateBookingCommand)
    assert command.source_channel is ChannelKind.WEB_CHAT
    assert command.client_ip_address == "198.51.100.4"
