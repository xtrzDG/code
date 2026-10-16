"""
Taps on a business bot's inline buttons: which ones are read back as the
customer's message, how they are acknowledged, and when a bot is asked
again for taps.
"""

import logging
from typing import Any

import pytest

from app.adapters.channels.telegram_tap_updates import TelegramTapUpdates
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.schemas.typings.channels.strings import ChannelSecret
from app.utilities.channels.telegram_taps import chosen_text, read_tap
from tests.channels.channels_payloads import telegram_ok
from tests.channels.channels_settings import build_settings
from tests.channels.recording_transport import RecordingTransport
from tests.channels.testbed import ChannelsTestbed
from tests.media.recorded_payloads import as_payload

BOT_TOKEN: ChannelSecret = ChannelSecret("123456:test-token-0000")
KEYBOARD: dict[str, Any] = {
    "inline_keyboard": [
        [{"text": "19:30", "callback_data": "19:30"}],
        [{"text": "🍷" * 17, "callback_data": "#2"}],
    ]
}


def tap_update(
    data: str = "19:30",
    chat_type: str = "private",
    is_bot: bool = False,
    markup: dict[str, Any] | None = KEYBOARD,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "message_id": 301,
        "date": 1,
        "chat": {"id": 555000111, "type": chat_type},
        "text": "Which time suits you?",
    }
    if markup is not None:
        message["reply_markup"] = markup
    return {
        "update_id": 7,
        "callback_query": {
            "id": "q-1",
            "from": {"id": 555000111, "is_bot": is_bot, "first_name": "Ana"},
            "message": message,
            "chat_instance": "-1",
            "data": data,
        },
    }


class TestReadingTaps:
    def test_a_tap_is_the_label_of_its_button(self) -> None:
        tap = read_tap(tap_update())

        assert tap is not None
        assert (tap.label, tap.chat_id, tap.message_id) == ("19:30", "555000111", "301")

    def test_a_numbered_tap_is_read_back_from_the_keyboard(self) -> None:
        tap = read_tap(tap_update("#2"))

        assert tap is not None
        assert tap.label == "🍷" * 17

    def test_a_numbered_tap_without_its_keyboard_is_dropped(self) -> None:
        assert read_tap(tap_update("#2", markup=None)) is None
        # An older message without its keyboard still gives the option.
        tap = read_tap(tap_update("19:30", markup=None))
        assert tap is not None
        assert tap.label == "19:30"

    @pytest.mark.parametrize(
        "update",
        [
            tap_update(chat_type="group"),
            tap_update(is_bot=True),
            tap_update(data=""),
            {"update_id": 1, "callback_query": {"id": "q"}},
            {"update_id": 1, "message": {"text": "hi"}},
            None,
        ],
    )
    def test_other_taps_are_not_messages(self, update: dict[str, Any] | None) -> None:
        assert read_tap(update) is None

    def test_the_adapter_gives_one_message_per_tap(self) -> None:
        adapter = ChannelsTestbed().telegram_adapter

        [message] = adapter.parse_webhook(as_payload(tap_update()))

        assert message.text == "19:30"
        assert message.provider_message_id == "555000111:tap-q-1"
        assert message.contact_name == "Ana"

    def test_the_chosen_option_closes_the_tapped_message(self) -> None:
        assert chosen_text("Which time suits you?\n", "19:30") == (
            "Which time suits you?\n\n✓ 19:30"
        )


class TestAcknowledging:
    def test_a_refused_answer_is_logged_and_nothing_breaks(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.respond(
            "POST",
            r"/answerCallbackQuery$",
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: query is too old",
            },
            status_code=400,
        )

        with caplog.at_level(logging.INFO, logger="app"):
            testbed.telegram_adapter.acknowledge_taps(
                as_payload(tap_update()), BOT_TOKEN
            )

        assert testbed.telegram_transport.requests_to("/editMessageText") == []
        assert "not acknowledged" in caplog.text
        assert str(BOT_TOKEN) not in caplog.text

    def test_without_a_token_or_a_tap_nothing_is_called(self) -> None:
        testbed = ChannelsTestbed()

        testbed.telegram_adapter.acknowledge_taps(as_payload(tap_update()), None)
        testbed.telegram_adapter.acknowledge_taps(
            as_payload({"update_id": 1, "message": {"text": "hi"}}), BOT_TOKEN
        )

        assert testbed.telegram_transport.requests == []


class TestTapUpdates:
    def build(
        self, transport: RecordingTransport, **settings: str
    ) -> TelegramTapUpdates:
        return TelegramTapUpdates(
            TelegramBotClient(transport=transport.build()), build_settings(**settings)
        )

    def test_a_bot_without_a_webhook_cannot_receive_taps(self) -> None:
        transport = RecordingTransport()
        transport.respond("POST", r"/getWebhookInfo$", telegram_ok({"url": ""}))

        assert self.build(transport).ensure(BOT_TOKEN) is False
        assert transport.requests_to("/setWebhook") == []

    def test_without_the_platform_key_the_webhook_is_left_alone(self) -> None:
        transport = RecordingTransport()
        transport.respond(
            "POST",
            r"/getWebhookInfo$",
            telegram_ok(
                {"url": "https://api.example.com/hook", "allowed_updates": ["message"]}
            ),
        )

        tap_updates = self.build(transport, ENCRYPTION_KEYS="", ENCRYPTION_KEY="")

        assert tap_updates.ensure(BOT_TOKEN) is False
        assert transport.requests_to("/setWebhook") == []

    def test_a_failed_check_is_tried_again_next_time(self) -> None:
        transport = RecordingTransport()
        transport.respond_in_turn(
            "POST",
            r"/getWebhookInfo$",
            [
                (502, {"ok": False, "error_code": 502, "description": "Bad Gateway"}),
                (200, telegram_ok({"url": "https://api.example.com/hook"})),
            ],
        )
        tap_updates = self.build(transport)

        assert tap_updates.ensure(BOT_TOKEN) is False
        assert tap_updates.ensure(BOT_TOKEN) is True
        assert tap_updates.ensure(BOT_TOKEN) is True
        assert len(transport.requests_to("/getWebhookInfo")) == 2
