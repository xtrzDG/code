"""
A booking confirmed by button taps in a business's Telegram bot: the real
engine offers the free times and then yes or no (offer_choices), the real
Telegram adapter shows them as an inline keyboard, and each tap comes back
through the adapter as the customer's message.
"""

from typing import Any

from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelInboundMessage,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.conversations.strings import ChannelUserId
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import call_tool, say, scripted
from tests.channels.channels_settings import build_settings
from tests.channels.recording_transport import RecordingTransport
from tests.media.recorded_payloads import as_payload

BOT_TOKEN: ChannelSecret = ChannelSecret("123456:test-token-0000")
CHAT_ID: str = "555000111"
SENT: dict[str, object] = {
    "ok": True,
    "result": {"message_id": 301, "date": 1, "chat": {"id": 555000111}},
}
WEBHOOK_WITH_TAPS: dict[str, object] = {
    "ok": True,
    "result": {
        "url": "https://api.example.com/v1/channels/telegram/x/webhook",
        "allowed_updates": ["message", "callback_query"],
    },
}


class TelegramChat:
    """The customer's chat with the bot: what the bot sent, and taps on it."""

    def __init__(self) -> None:
        self.transport = RecordingTransport()
        self.transport.respond("POST", r"/sendMessage$", SENT)
        self.transport.respond("POST", r"/getWebhookInfo$", WEBHOOK_WITH_TAPS)
        self.adapter = TelegramChannelAdapter(
            TelegramBotClient(transport=self.transport.build()),
            PhoneNumberParser(),
            build_settings(),
        )
        self.target = ChannelDeliveryTarget(
            channel=ChannelKind.TELEGRAM,
            channel_user_id=ChannelUserId(CHAT_ID),
            credential=BOT_TOKEN,
        )

    def deliver(self, reply: AssistantReply) -> dict[str, Any]:
        assert reply.text is not None
        self.adapter.send(self.target, reply.text, reply.choices)
        sent: dict[str, Any] = self.transport.requests_to("/sendMessage")[-1].json()
        return sent

    def tap(self, sent: dict[str, Any], label: str) -> ChannelInboundMessage:
        keyboard: list[list[dict[str, str]]] = sent["reply_markup"]["inline_keyboard"]
        [button] = [b for row in keyboard for b in row if b["text"] == label]
        update = {
            "update_id": 900200,
            "callback_query": {
                "id": f"tap-of-{label}",
                "from": {"id": int(CHAT_ID), "is_bot": False, "first_name": "Ann"},
                "message": {
                    "message_id": 301,
                    "date": 1,
                    "chat": {"id": int(CHAT_ID), "type": "private"},
                    "text": sent["text"],
                    "reply_markup": sent["reply_markup"],
                },
                "chat_instance": "-1",
                "data": button["callback_data"],
            },
        }
        [message] = self.adapter.parse_webhook(as_payload(update))
        return message


def send_tap(world: BrainWorld, message: ChannelInboundMessage) -> AssistantReply:
    return world.send(
        str(message.text),
        channel=ChannelKind.TELEGRAM,
        user_id=str(message.channel_user_id),
        phone=None,
        name="Ann",
    )


def test_a_booking_is_confirmed_by_two_taps() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.CHECK_AVAILABILITY,
                '{"resource_type":"table","date":"2026-10-02","time":null,'
                '"party_size":2,"duration_minutes":null,"nights":null}',
            ),
            call_tool(
                AssistantToolName.OFFER_CHOICES,
                '{"prompt_text":"Which time suits you?","options":["19:30","20:00"]}',
            ),
            say("We have a table for 2 tomorrow."),
            call_tool(
                AssistantToolName.OFFER_CHOICES,
                '{"prompt_text":"Shall I book it?","options":["Yes, book it","No"]}',
            ),
            say("A table for 2 tomorrow at 20:00 for Ann."),
            call_tool(
                AssistantToolName.CREATE_BOOKING,
                '{"name":"Ann","phone":"+995555123456","resource_type":"table",'
                '"date":"2026-10-02","time":"20:00","party_size":2,'
                '"duration_minutes":null,"nights":null,"notes":null}',
            ),
            say("Booked: a table for 2 tomorrow at 20:00 for Ann."),
        )
    )
    chat = TelegramChat()

    offer = world.send(
        "A table for 2 tomorrow evening?",
        channel=ChannelKind.TELEGRAM,
        user_id=CHAT_ID,
        phone=None,
        name="Ann",
    )
    assert offer.choices is not None
    assert offer.text is not None
    assert str(offer.text).endswith(
        "We have a table for 2 tomorrow.\n\nWhich time suits you?"
    )
    times = chat.deliver(offer)
    assert [b["text"] for b in times["reply_markup"]["inline_keyboard"][0]] == [
        "19:30",
        "20:00",
    ]

    confirmation = send_tap(world, chat.tap(times, "20:00"))
    assert confirmation.choices is not None
    assert [str(option) for option in confirmation.choices.options] == [
        "Yes, book it",
        "No",
    ]
    assert world.bookings.commands == []
    question = chat.deliver(confirmation)

    booked = send_tap(world, chat.tap(question, "Yes, book it"))

    assert len(booked.created_booking_ids) == 1
    assert booked.choices is None
    [command] = world.bookings.commands
    assert isinstance(command, CreateBookingCommand)
    assert command.time == LocalTimeOfDay("20:00")
    assert command.source_channel is ChannelKind.TELEGRAM
    customer_lines = [
        str(message.text)
        for message in world.messages(booked.conversation_id)
        if message.author.value == "customer"
    ]
    assert customer_lines[1:] == ["20:00", "Yes, book it"]
    # The offered options are stored with each reply, in the reply language.
    stored = [
        message.choices
        for message in world.messages(booked.conversation_id)
        if message.choices is not None
    ]
    assert [[str(o) for o in choices.options] for choices in stored] == [
        ["19:30", "20:00"],
        ["Yes, book it", "No"],
    ]
    assert {str(choices.language) for choices in stored} == {"en"}
    # Until its release gate opens, offer_choices is not kept among a
    # message's tool calls (an older release could not read the name).
    assert [
        [call.tool_name for call in message.tool_calls]
        for message in world.messages(booked.conversation_id)
        if message.tool_calls
    ] == [[AssistantToolName.CHECK_AVAILABILITY], [AssistantToolName.CREATE_BOOKING]]
