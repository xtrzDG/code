"""
A Telegram reply that offers options: an inline keyboard under its last
part, the bot's webhook asked once for button taps, and the numbered list
whenever the keyboard cannot be used.
"""

from typing import Any

from app.schemas.domain.reply_choices import ReplyChoices
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.conversations.constrained_strings import (
    ChoiceLabel,
    ChoicePromptText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.channels.channels_payloads import telegram_ok
from tests.channels.channels_settings import ENCRYPTION_KEY, TELEGRAM_BOT_TOKEN
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed
from tests.contracts.vendor_schemas import assert_outbound

SPEC: str = "telegram_bot_api.json"
WEBHOOK_URL: str = "https://api.example.com/v1/channels/telegram/x/webhook"
REFUSED: dict[str, object] = {
    "ok": False,
    "error_code": 400,
    "description": "Bad Request: BUTTON_DATA_INVALID",
}


def choices(*options: str) -> ReplyChoices:
    return ReplyChoices(
        prompt=ChoicePromptText("Which time suits you?"),
        options=[ChoiceLabel(option) for option in options],
        language=LanguageTag("en"),
    )


def webhook_info(allowed_updates: list[str] | None) -> dict[str, object]:
    result: dict[str, object] = {"url": WEBHOOK_URL, "pending_update_count": 0}
    if allowed_updates is not None:
        result["allowed_updates"] = allowed_updates
    return telegram_ok(result)


def answered(testbed: ChannelsTestbed, *texts: str) -> list[dict[str, Any]]:
    """The bot's messages after the customer wrote each text."""

    _, channel = connect_bot(testbed)
    for number, text in enumerate(texts, start=1):
        post_update(testbed, channel, build_update(text, message_id=number))
        testbed.run_worker()
    return [
        request.json()
        for request in testbed.telegram_transport.requests_to("/sendMessage")
    ]


def test_options_go_as_an_inline_keyboard_under_the_reply() -> None:
    testbed = ChannelsTestbed()
    testbed.telegram_transport.respond(
        "POST", r"/getWebhookInfo$", webhook_info(["message", "callback_query"])
    )
    testbed.pipeline.reply_text = "We have a table.\n\nWhich time suits you?"
    testbed.pipeline.reply_choices = choices("18:00", "19:30", "21:00", "22:00")

    first, second = answered(testbed, "A table tonight?", "And tomorrow?")

    assert first["text"] == "We have a table.\n\nWhich time suits you?"
    assert first["reply_markup"] == {
        "inline_keyboard": [
            [
                {"text": "18:00", "callback_data": "18:00"},
                {"text": "19:30", "callback_data": "19:30"},
                {"text": "21:00", "callback_data": "21:00"},
            ],
            [{"text": "22:00", "callback_data": "22:00"}],
        ]
    }
    assert_outbound(first, SPEC, "request:sendMessage")
    assert second["reply_markup"] == first["reply_markup"]
    # The bot's webhook is checked once per process, not before every reply.
    assert len(testbed.telegram_transport.requests_to("/getWebhookInfo")) == 1
    assert testbed.telegram_transport.requests_to("/setWebhook") == []


def test_longer_labels_stand_two_in_a_row() -> None:
    testbed = ChannelsTestbed()
    testbed.telegram_transport.respond("POST", r"/getWebhookInfo$", webhook_info(None))
    testbed.pipeline.reply_choices = choices("Ბაღის მაგიდა", "Window table")

    [sent] = answered(testbed, "Where can I sit?")

    # Labels of up to 8 characters go three in a row, up to 14 two.
    assert sent["reply_markup"]["inline_keyboard"] == [
        [
            {"text": "Ბაღის მაგიდა", "callback_data": "Ბაღის მაგიდა"},
            {"text": "Window table", "callback_data": "Window table"},
        ]
    ]


def test_a_bot_connected_before_buttons_is_registered_again_for_taps() -> None:
    testbed = ChannelsTestbed()
    testbed.telegram_transport.respond(
        "POST", r"/getWebhookInfo$", webhook_info(["message"])
    )
    testbed.telegram_transport.respond("POST", r"/setWebhook$", telegram_ok(True))
    testbed.pipeline.reply_choices = choices("Yes", "No")

    [sent] = answered(testbed, "Can I book?")

    [registration] = testbed.telegram_transport.requests_to("/setWebhook")
    assert registration.json()["url"] == WEBHOOK_URL
    assert registration.json()["allowed_updates"] == ["message", "callback_query"]
    assert registration.json()["secret_token"] == str(
        derive_telegram_webhook_secret(
            PlatformSecret(ENCRYPTION_KEY), ChannelSecret(TELEGRAM_BOT_TOKEN)
        )
    )
    assert_outbound(registration.json(), SPEC, "request:setWebhook")
    assert "reply_markup" in sent


def test_a_bot_that_cannot_be_checked_gets_a_numbered_list() -> None:
    testbed = ChannelsTestbed()
    testbed.telegram_transport.respond(
        "POST",
        r"/getWebhookInfo$",
        {"ok": False, "error_code": 500, "description": "Internal Server Error"},
        status_code=500,
    )
    testbed.pipeline.reply_text = "We have a table.\n\nWhich time suits you?"
    testbed.pipeline.reply_choices = choices("18:00", "19:30")

    [sent] = answered(testbed, "A table tonight?")

    assert "reply_markup" not in sent
    assert sent["text"] == (
        "We have a table.\n\nWhich time suits you?\n\n1. 18:00\n2. 19:30"
    )


def test_a_refused_keyboard_is_sent_again_as_a_numbered_list() -> None:
    testbed = ChannelsTestbed()
    testbed.telegram_transport.respond("POST", r"/getWebhookInfo$", webhook_info(None))
    testbed.pipeline.reply_text = "Which time suits you?"
    testbed.pipeline.reply_choices = choices("18:00", "19:30")
    _, channel = connect_bot(testbed)
    testbed.telegram_transport.respond_in_turn(
        "POST", r"/sendMessage$", [(400, REFUSED), (200, telegram_ok({}))]
    )

    post_update(testbed, channel, build_update("A table tonight?"))
    testbed.run_worker()

    with_keyboard, numbered = [
        request.json()
        for request in testbed.telegram_transport.requests_to("/sendMessage")
    ]
    assert "reply_markup" in with_keyboard
    assert "reply_markup" not in numbered
    assert numbered["text"] == "Which time suits you?\n\n1. 18:00\n2. 19:30"


def test_only_the_last_part_of_a_long_reply_carries_the_keyboard() -> None:
    testbed = ChannelsTestbed()
    testbed.telegram_transport.respond("POST", r"/getWebhookInfo$", webhook_info(None))
    testbed.pipeline.reply_text = ("Our menu and prices. " * 300).strip()
    testbed.pipeline.reply_choices = choices("18:00", "19:30")

    parts = answered(testbed, "Menu?")

    assert len(parts) == 2
    assert "reply_markup" not in parts[0]
    assert "reply_markup" in parts[1]
    # Each part leaves room for the numbered list it may fall back to.
    assert all(
        len(part["text"]) <= 4096 - len("\n\n1. 18:00\n2. 19:30") for part in parts
    )
