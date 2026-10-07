"""The Messenger and Instagram page channels."""

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelWebhookPayload,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.strings import ChannelExternalId, ChannelSecret
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from tests.channels.channels_payloads import to_json_bytes
from tests.channels.channels_settings import PAGE_ACCESS_TOKEN
from tests.channels.meta_payloads import (
    INSTAGRAM_ID,
    PAGE_ID,
    page_message,
    page_webhook,
)
from tests.channels.testbed import ChannelsTestbed


class TestPageChannels:
    def test_messenger_text_and_postbacks(self) -> None:
        adapter = ChannelsTestbed().messenger_adapter
        events = [
            page_message("psid-1", "Is the arena free on Saturday?", PAGE_ID),
            {
                "sender": {"id": "psid-2"},
                "recipient": {"id": PAGE_ID},
                "postback": {"title": "Book a table", "payload": "BOOK", "mid": "m2"},
            },
        ]
        messages = adapter.parse_webhook(
            ChannelWebhookPayload(
                body=to_json_bytes(page_webhook("page", PAGE_ID, events))
            )
        )

        assert [(m.channel_user_id, m.text) for m in messages] == [
            ("psid-1", "Is the arena free on Saturday?"),
            ("psid-2", "Book a table"),
        ]
        assert all(m.account_id == PAGE_ID for m in messages)
        assert all(m.channel is ChannelKind.MESSENGER for m in messages)

    def test_echoes_own_messages_reads_and_attachments_are_skipped(self) -> None:
        adapter = ChannelsTestbed().instagram_adapter
        events = [
            page_message(
                "igsid-1", "Reply from the business", INSTAGRAM_ID, is_echo=True
            ),
            page_message(INSTAGRAM_ID, "Sent by the account itself", INSTAGRAM_ID),
            page_message("igsid-1", None, INSTAGRAM_ID),
            {"sender": {"id": "igsid-1"}, "read": {"mid": "m"}},
            {"sender": {"id": "igsid-1"}, "reaction": {"reaction": "love"}},
            page_message("igsid-1", "مرحبا، هل لديكم طاولة؟", INSTAGRAM_ID, mid="m9"),
        ]
        messages = adapter.parse_webhook(
            ChannelWebhookPayload(
                body=to_json_bytes(page_webhook("instagram", INSTAGRAM_ID, events))
            )
        )

        assert len(messages) == 1
        assert messages[0].channel is ChannelKind.INSTAGRAM
        assert messages[0].text == "مرحبا، هل لديكم طاولة؟"
        assert messages[0].provider_message_id == "m9"

    def test_each_adapter_reads_only_its_object(self) -> None:
        testbed = ChannelsTestbed()
        payload = ChannelWebhookPayload(
            body=to_json_bytes(
                page_webhook("instagram", INSTAGRAM_ID, [page_message("1", "x", "2")])
            )
        )
        assert testbed.messenger_adapter.parse_webhook(payload) == []
        assert testbed.whatsapp_adapter.parse_webhook(payload) == []

    def test_replies_use_the_page_token_and_the_channel_limit(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond("POST", r"/me/messages$", {"message_id": "m"})
        target = ChannelDeliveryTarget(
            channel=ChannelKind.INSTAGRAM,
            account_id=ChannelExternalId(INSTAGRAM_ID),
            channel_user_id=ChannelUserId("igsid-1"),
            credential=ChannelSecret(PAGE_ACCESS_TOKEN),
        )

        delivered = testbed.instagram_adapter.send(target, MessageText("Ok. " * 400))

        assert delivered.delivered == 2
        requests = testbed.meta_transport.requests
        assert all(
            r.headers["Authorization"] == f"Bearer {PAGE_ACCESS_TOKEN}"
            for r in requests
        )
        assert all(len(r.json()["message"]["text"]) <= 1000 for r in requests)
        assert requests[0].json()["recipient"] == {"id": "igsid-1"}
        assert requests[0].json()["messaging_type"] == "RESPONSE"
        assert PAGE_ACCESS_TOKEN not in repr(target)

        missing_token = target.model_copy(update={"credential": None})
        with pytest.raises(ExternalServiceError):
            testbed.messenger_adapter.send(missing_token, MessageText("Hi"))
