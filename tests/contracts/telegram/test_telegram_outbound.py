"""
The Bot API methods the platform calls (getMe, getUserProfilePhotos,
setWebhook, deleteWebhook, sendMessage, sendChatAction, getFile): every
request matches the Bot API specification with every object closed, the
documented answers are read as expected, and the documented error answers
become the application errors the delivery and setup flows rely on.
"""

from typing import Any

import pytest

from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.clients.telegram.telegram_file_client import TelegramFileClient
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    TelegramBotUserId,
    TelegramWebhookSecret,
)
from app.schemas.typings.channels.strings import OutboundMessagePart
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.media.strings import ProviderMediaId
from app.schemas.typings.platform.strings import PlatformSecret
from tests.channels.channels_payloads import telegram_ok
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

SPEC: str = "telegram_bot_api.json"
TOKEN = PlatformSecret("123456789:test-token-0000")
CHAT = ChannelUserId("555000111")


def fixture(name: str) -> Any:
    return load_json_fixture("telegram", name)


def scripted_transport() -> RecordingTransport:
    transport = RecordingTransport()
    transport.respond("POST", r"/getMe$", fixture("telegram_get_me_response.json"))
    transport.respond(
        "POST",
        r"/getUserProfilePhotos$",
        fixture("telegram_profile_photos_response.json"),
    )
    transport.respond(
        "POST", r"/sendMessage$", fixture("telegram_send_message_response.json")
    )
    transport.respond("POST", r"/getFile$", fixture("telegram_get_file_response.json"))
    for method in ("setWebhook", "deleteWebhook", "sendChatAction"):
        transport.respond("POST", rf"/{method}$", telegram_ok())
    return transport


@pytest.mark.parametrize(
    ("name", "root"),
    [
        ("telegram_get_me_response.json", "User"),
        ("telegram_send_message_response.json", "Message"),
        ("telegram_get_file_response.json", "File"),
        ("telegram_profile_photos_response.json", "UserProfilePhotos"),
    ],
)
def test_documented_answers_match_the_specification(name: str, root: str) -> None:
    answer: dict[str, Any] = fixture(name)

    assert answer["ok"] is True
    assert_inbound(answer["result"], SPEC, root)


def test_bot_setup_requests_match_the_specification() -> None:
    transport = scripted_transport()
    client = TelegramBotClient(transport=transport.build())

    profile = client.get_me(TOKEN)
    photo = client.get_profile_photo_file_id(TOKEN, TelegramBotUserId("7012345678"))
    client.set_webhook(
        TOKEN,
        ChannelWebhookUrl("https://api.example.com/v1/channels/telegram/ch_1/webhook"),
        TelegramWebhookSecret("a" * 64),
    )
    client.delete_webhook(TOKEN)

    assert str(profile.username) == "funicular_vr_bot"
    # The smallest photo at least 96 px wide.
    assert photo == "AgACAgIAAxUAAWZx-photo-small-0000"
    methods = [request.path.rsplit("/", 1)[-1] for request in transport.requests]
    assert methods == ["getMe", "getUserProfilePhotos", "setWebhook", "deleteWebhook"]
    for request in transport.requests[1:]:
        method: str = request.path.rsplit("/", 1)[-1]
        assert_outbound(request.json(), SPEC, f"request:{method}")


def test_message_typing_and_file_requests_match_the_specification() -> None:
    transport = scripted_transport()
    bot = TelegramBotClient(transport=transport.build())

    message_id = bot.send_message(
        TOKEN, CHAT, OutboundMessagePart("На субботу есть столик.")
    )
    bot.send_typing_action(TOKEN, CHAT)
    file_info = TelegramFileClient(transport=transport.build()).get_file(
        TOKEN, ProviderMediaId("AwACAgIAAxkBAAIBY2Zx-voice-file-0000")
    )

    assert message_id == "555000111:205"
    assert str(file_info.file_path) == "voice/file_7.oga"
    assert file_info.file_size == 15360
    for request in transport.requests:
        method: str = request.path.rsplit("/", 1)[-1]
        assert_outbound(request.json(), SPEC, f"request:{method}")


@pytest.mark.parametrize(
    "case",
    fixture("telegram_errors.json")["cases"],
    ids=lambda case: f"{case['status']}",
)
def test_documented_errors_become_application_errors(case: dict[str, Any]) -> None:
    transport = RecordingTransport()
    transport.respond("POST", r"/sendMessage$", case["body"], case["status"])
    client = TelegramBotClient(transport=transport.build())

    with pytest.raises(ApplicationError) as raised:
        client.send_message(TOKEN, CHAT, OutboundMessagePart("Hello"))

    assert type(raised.value).__name__ == case["expected"]
