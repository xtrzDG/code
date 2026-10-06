"""
Telegram Bot API updates through the real channel adapter and the
business bot's webhook route. Every fixture matches the Bot API
specification (the community OpenAPI document generated from
core.telegram.org/bots/api); only new private messages from people are
answered (a tap on the bot's buttons as the option's text, the tap then
answered and the tapped message edited), every other kind of update is
skipped, logged by kind and acknowledged with 200.
"""

import logging
from typing import Any

import pytest

from app.utilities.channels.channel_endpoints import TELEGRAM_SECRET_HEADER
from tests.channels.channels_payloads import telegram_ok
from tests.channels.telegram_updates import BOT_SECRET, connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed
from tests.contracts.contract_files import fixture_names, load_json_fixture
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound
from tests.media.recorded_payloads import as_payload

SPEC: str = "telegram_bot_api.json"
ANNA: dict[str, Any] = {
    "channel": "telegram",
    "customer": "555000111",
    "name": "Anna Kapanadze",
    "attachments": [],
    "source": None,
}
# fixture -> the normalized customer message, or the kind skipped.
EXPECTED: dict[str, dict[str, Any] | str] = {
    "telegram_message.json": {
        **ANNA,
        "text": "Здравствуйте! Можно забронировать на субботу?",
        "id": "555000111:201",
    },
    "telegram_start_with_source.json": {
        **ANNA,
        "text": "/start",
        "id": "555000111:202",
        "source": "flyer",
    },
    "telegram_voice.json": {
        **ANNA,
        "text": "",
        "id": "555000111:203",
        "attachments": ["audio"],
    },
    "telegram_edited_message.json": "edited_message=1",
    # A tap on a button of the bot's keyboard: the option, under an id of
    # its own.
    "telegram_callback_query.json": {
        **ANNA,
        "text": "19:30",
        "id": "555000111:tap-4382bfdwdsb323b2d9",
    },
    "telegram_my_chat_member.json": "my_chat_member=1",
    "telegram_group_message.json": "message:not a private chat=1",
    "telegram_unknown_update.json": "other=1",
}
UPDATE_FIXTURES: list[str] = sorted(EXPECTED)


def test_every_update_fixture_has_an_expectation() -> None:
    updates = [
        name
        for name in fixture_names("telegram")
        if not name.endswith("_response.json") and name != "telegram_errors.json"
    ]
    assert sorted(updates) == sorted([*UPDATE_FIXTURES, "telegram_media_updates.json"])


@pytest.mark.parametrize("fixture", UPDATE_FIXTURES)
def test_update_matches_the_bot_api_specification(fixture: str) -> None:
    assert_inbound(load_json_fixture("telegram", fixture), SPEC, "Update")


def test_media_updates_match_the_bot_api_specification() -> None:
    for update in load_json_fixture("telegram", "telegram_media_updates.json"):
        assert_inbound(update, SPEC, "Update")


@pytest.mark.parametrize("fixture", UPDATE_FIXTURES)
def test_adapter_reads_private_messages_and_logs_the_rest(
    fixture: str, caplog: pytest.LogCaptureFixture
) -> None:
    adapter = ChannelsTestbed().telegram_adapter
    with caplog.at_level(logging.INFO, logger="app"):
        messages = adapter.parse_webhook(
            as_payload(load_json_fixture("telegram", fixture))
        )

    expected = EXPECTED[fixture]
    if isinstance(expected, str):
        assert messages == []
        [record] = caplog.records
        assert record.getMessage().endswith(f": {expected}.")
        return

    [message] = messages
    assert {
        "channel": message.channel.value,
        "customer": str(message.channel_user_id),
        "name": None if message.contact_name is None else str(message.contact_name),
        "text": str(message.text),
        "id": str(message.provider_message_id),
        "attachments": [attachment.kind.value for attachment in message.attachments],
        "source": (
            None
            if message.acquisition_source is None
            else str(message.acquisition_source)
        ),
    } == expected
    assert caplog.records == []


@pytest.mark.parametrize("fixture", UPDATE_FIXTURES)
def test_webhook_acknowledges_every_kind_and_replies_match_the_spec(
    fixture: str,
) -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    testbed.telegram_transport.respond(
        "POST",
        r"/sendMessage$",
        load_json_fixture("telegram", "telegram_send_message_response.json"),
    )
    testbed.telegram_transport.respond("POST", r"/sendChatAction$", telegram_ok())
    testbed.telegram_transport.respond(
        "POST", r"/answerCallbackQuery$", telegram_ok(True)
    )
    testbed.telegram_transport.respond("POST", r"/editMessageText$", telegram_ok({}))

    response = post_update(testbed, channel, load_json_fixture("telegram", fixture))
    testbed.run_worker()

    assert response.status_code == 200
    replies = testbed.telegram_transport.requests_to("/sendMessage")
    assert len(replies) == (0 if isinstance(EXPECTED[fixture], str) else 1)
    for reply in replies:
        assert_outbound(reply.json(), SPEC, "request:sendMessage")
    for action in testbed.telegram_transport.requests_to("/sendChatAction"):
        assert_outbound(action.json(), SPEC, "request:sendChatAction")
    answers = testbed.telegram_transport.requests_to("/answerCallbackQuery")
    edits = testbed.telegram_transport.requests_to("/editMessageText")
    is_tap = fixture == "telegram_callback_query.json"
    assert (len(answers), len(edits)) == ((1, 1) if is_tap else (0, 0))
    for answer in answers:
        assert_outbound(answer.json(), SPEC, "request:answerCallbackQuery")
    for edit in edits:
        assert_outbound(edit.json(), SPEC, "request:editMessageText")
        assert edit.json()["text"].endswith("\n\n✓ 19:30")


@pytest.mark.parametrize(
    "body", [b"not json", b"[]", b"{}", b'{"update_id": 1, "message": "oops"}']
)
def test_malformed_updates_are_acknowledged(body: bytes) -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)

    response = testbed.build_http_client().post(
        f"/v1/channels/telegram/{channel.id}/webhook",
        content=body,
        headers={TELEGRAM_SECRET_HEADER: BOT_SECRET},
    )

    assert response.status_code == 200
