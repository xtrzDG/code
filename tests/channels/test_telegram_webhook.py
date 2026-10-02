"""The Telegram webhook route: secrets, routing to the business, replies."""

import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.channel_endpoints import TELEGRAM_SECRET_HEADER
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.channels.channels_payloads import to_json_bytes
from tests.channels.channels_settings import (
    ENCRYPTION_KEY,
    OTHER_TELEGRAM_BOT_TOKEN,
    TELEGRAM_BOT_TOKEN,
)
from tests.channels.telegram_updates import (
    BOT_SECRET,
    build_update,
    connect_bot,
    post_update,
)
from tests.channels.testbed import ChannelsTestbed


class TestTelegramWebhook:
    def test_message_is_acknowledged_then_answered_by_the_worker(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)

        response = post_update(testbed, channel, build_update())

        assert response.status_code == 200
        assert response.json() == {
            "received": 1,
            "answered": 0,
            "silenced": 0,
            "failed": 0,
            "queued": 1,
            "duplicates": 0,
        }
        # The request only stored the message; nothing was asked or sent.
        assert testbed.pipeline.messages == []
        assert testbed.telegram_transport.requests_to("/sendMessage") == []

        testbed.run_worker()

        [inbound] = testbed.pipeline.messages
        assert inbound.business_id == business.id
        assert inbound.channel is ChannelKind.TELEGRAM
        assert inbound.channel_user_id == "555000111"
        [sent] = testbed.telegram_transport.requests_to("/sendMessage")
        assert sent.path == f"/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        assert sent.json()["chat_id"] == "555000111"
        assert sent.json()["text"] == "Reply: Do you have a table for 4 tonight?"

    def test_long_reply_is_split_into_several_messages(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.pipeline.reply_text = ("Меню и цены. " * 400).strip()

        post_update(testbed, channel, build_update())
        testbed.run_worker()

        sent = testbed.telegram_transport.requests_to("/sendMessage")
        assert len(sent) == 2
        assert all(len(request.json()["text"]) <= 4096 for request in sent)

    def test_assistant_stays_silent_while_staff_handle_the_chat(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.pipeline.is_silent = True

        post_update(testbed, channel, build_update())
        testbed.run_worker()

        assert len(testbed.pipeline.messages) == 1
        assert testbed.telegram_transport.requests_to("/sendMessage") == []

    def test_repeated_delivery_is_answered_once(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)

        post_update(testbed, channel, build_update())
        second = post_update(testbed, channel, build_update())
        testbed.run_worker()

        assert second.json()["queued"] == 0
        assert second.json()["duplicates"] == 1
        assert len(testbed.pipeline.messages) == 1
        assert len(testbed.telegram_transport.requests_to("/sendMessage")) == 1

    @pytest.mark.parametrize("secret", [None, "wrong", BOT_SECRET.upper()])
    def test_wrong_or_missing_secret_is_refused(self, secret: str | None) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)

        response = post_update(testbed, channel, build_update(), secret=secret)

        assert response.status_code == 401
        assert testbed.pipeline.messages == []

    def test_secret_of_another_bot_is_refused(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        other_secret = derive_telegram_webhook_secret(
            PlatformSecret(ENCRYPTION_KEY), ChannelSecret(OTHER_TELEGRAM_BOT_TOKEN)
        )

        response = post_update(testbed, channel, build_update(), str(other_secret))

        assert response.status_code == 401

    def test_unknown_disabled_or_foreign_channels_are_not_found(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        whatsapp = testbed.add_channel(business.id, ChannelKind.WHATSAPP, "1000")
        disabled = testbed.add_channel(
            business.id,
            ChannelKind.TELEGRAM,
            "old_bot",
            TELEGRAM_BOT_TOKEN,
            status=ChannelStatus.DISABLED,
        )
        client = testbed.build_http_client()

        for channel_id in ("channel_not-an-id", str(whatsapp.id), str(disabled.id)):
            response = client.post(
                f"/v1/channels/telegram/{channel_id}/webhook",
                content=to_json_bytes(build_update()),
                headers={TELEGRAM_SECRET_HEADER: BOT_SECRET},
            )
            assert response.status_code == 404

        assert channel.status is ChannelStatus.CONNECTED

    def test_engine_failures_are_retried_and_never_lose_the_message(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.pipeline.failure = ExternalServiceError("model unavailable")

        response = post_update(testbed, channel, build_update())
        testbed.run_worker()

        assert response.status_code == 200
        assert response.json()["queued"] == 1
        assert testbed.telegram_transport.requests_to("/sendMessage") == []

        # The job runs again after its backoff, and the customer is answered.
        testbed.pipeline.failure = None
        testbed.clock.advance(60)
        testbed.run_worker()

        [sent] = testbed.telegram_transport.requests_to("/sendMessage")
        assert sent.json()["text"] == "Reply: Do you have a table for 4 tonight?"
