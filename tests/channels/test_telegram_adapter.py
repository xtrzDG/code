"""The Telegram bot client and channel adapter."""

from typing import Any

import httpx
import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.media import AttachmentKind
from app.schemas.dto.channels.channel_webhooks import ChannelWebhookPayload
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    TelegramWebhookSecret,
)
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    OutboundMessagePart,
    WebhookSignatureHeader,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.channels.channels_payloads import telegram_ok, to_json_bytes
from tests.channels.channels_settings import (
    ENCRYPTION_KEY,
    OTHER_TELEGRAM_BOT_TOKEN,
    TELEGRAM_BOT_TOKEN,
)
from tests.channels.telegram_updates import BOT_SECRET, build_update
from tests.channels.testbed import ChannelsTestbed


class TestTelegramBotClient:
    def test_get_me_reads_the_username(self) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.respond(
            "POST",
            r"/getMe$",
            telegram_ok({"id": 1, "is_bot": True, "username": "funicular_vr_bot"}),
        )

        profile = testbed.telegram_client.get_me(ChannelSecret(TELEGRAM_BOT_TOKEN))

        assert profile.username == "funicular_vr_bot"
        request = testbed.telegram_transport.requests[0]
        assert request.path == f"/bot{TELEGRAM_BOT_TOKEN}/getMe"

    def test_rejected_token_is_a_validation_error_without_the_token(self) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.respond(
            "POST",
            r"/getMe$",
            {"ok": False, "error_code": 401, "description": "Unauthorized"},
            status_code=401,
        )

        with pytest.raises(ValidationFailedError) as error:
            testbed.telegram_client.get_me(ChannelSecret(TELEGRAM_BOT_TOKEN))

        assert TELEGRAM_BOT_TOKEN not in str(error.value)

    def test_transport_errors_never_carry_the_token(self) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.failure = httpx.ConnectError(
            f"cannot reach /bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        )

        with pytest.raises(ExternalServiceError) as error:
            testbed.telegram_client.send_message(
                ChannelSecret(TELEGRAM_BOT_TOKEN),
                ChannelUserId("1"),
                OutboundMessagePart("hi"),
            )

        assert TELEGRAM_BOT_TOKEN not in str(error.value)
        assert error.value.__cause__ is None
        assert error.value.__suppress_context__

    def test_set_webhook_payload(self) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.respond("POST", r"/setWebhook$", telegram_ok())

        testbed.telegram_client.set_webhook(
            ChannelSecret(TELEGRAM_BOT_TOKEN),
            ChannelWebhookUrl(
                "https://api.workshop.test/v1/channels/telegram/x/webhook"
            ),
            TelegramWebhookSecret(BOT_SECRET),
        )

        assert testbed.telegram_transport.requests[0].json() == {
            "url": "https://api.workshop.test/v1/channels/telegram/x/webhook",
            "secret_token": BOT_SECRET,
            "allowed_updates": ["message", "callback_query"],
            "drop_pending_updates": False,
        }

    def test_api_errors_and_non_json_answers(self) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.respond(
            "POST",
            r"/sendMessage$",
            {"ok": False, "error_code": 403, "description": "bot was blocked"},
            status_code=403,
        )
        with pytest.raises(ExternalServiceError, match="bot was blocked"):
            testbed.telegram_client.send_message(
                ChannelSecret(TELEGRAM_BOT_TOKEN),
                ChannelUserId("1"),
                OutboundMessagePart("hi"),
            )

        testbed.telegram_transport.respond("POST", r"/getMe$", telegram_ok({}))
        with pytest.raises(ExternalServiceError):
            testbed.telegram_client.get_me(ChannelSecret(TELEGRAM_BOT_TOKEN))


class TestTelegramAdapter:
    def payload(self, update: dict[str, Any]) -> ChannelWebhookPayload:
        return ChannelWebhookPayload(body=to_json_bytes(update))

    def test_private_text_message(self) -> None:
        testbed = ChannelsTestbed()
        [message] = testbed.telegram_adapter.parse_webhook(
            self.payload(build_update("გამარჯობა! მაგიდა მინდა"))
        )

        assert message.channel is ChannelKind.TELEGRAM
        assert message.channel_user_id == "555000111"
        assert message.text == "გამარჯობა! მაგიდა მინდა"
        assert message.contact_name == "ნინო Beridze"
        assert message.provider_message_id == "555000111:17"
        assert message.account_id is None

    def test_own_shared_contact_gives_the_phone_number(self) -> None:
        testbed = ChannelsTestbed()
        own_contact = {"phone_number": "995599123456", "user_id": 555_000_111}
        [message] = testbed.telegram_adapter.parse_webhook(
            self.payload(build_update(text=None, contact=own_contact))
        )

        assert message.contact_phone_number == "+995599123456"
        assert message.text == "+995599123456"

    def test_someone_elses_contact_is_not_the_customer_phone(self) -> None:
        testbed = ChannelsTestbed()
        friend = {"phone_number": "+48512345678", "user_id": 42}
        [card] = testbed.telegram_adapter.parse_webhook(
            self.payload(build_update(text=None, contact=friend))
        )
        # A contact card the assistant cannot read: it still gets an answer.
        assert card.text == ""
        assert card.contact_phone_number is None
        assert [attachment.kind for attachment in card.attachments] == [
            AttachmentKind.CONTACT
        ]

        [message] = testbed.telegram_adapter.parse_webhook(
            self.payload(build_update(text="Call my friend", contact=friend))
        )
        assert message.contact_phone_number is None

    @pytest.mark.parametrize(
        "update",
        [
            build_update(chat_type="group"),
            build_update(chat_type="supergroup"),
            build_update(is_bot=True),
            build_update(text=None),
            {"update_id": 1, "edited_message": build_update()["message"]},
            {"update_id": 1, "message": {"text": "no chat"}},
            {"update_id": 1},
        ],
    )
    def test_other_updates_are_skipped(self, update: dict[str, Any]) -> None:
        assert (
            ChannelsTestbed().telegram_adapter.parse_webhook(self.payload(update)) == []
        )

    def test_malformed_bodies_are_skipped(self) -> None:
        adapter = ChannelsTestbed().telegram_adapter
        for body in (b"", b"[]", b"{not json", "ü".encode("latin-1")):
            assert adapter.parse_webhook(ChannelWebhookPayload(body=body)) == []

    def test_signature_needs_the_secret_of_this_bot(self) -> None:
        adapter = ChannelsTestbed().telegram_adapter
        token = ChannelSecret(TELEGRAM_BOT_TOKEN)
        valid = ChannelWebhookPayload(
            body=b"{}", signature_header=WebhookSignatureHeader(BOT_SECRET)
        )
        adapter.verify_signature(valid, token)

        other_bot_secret = derive_telegram_webhook_secret(
            PlatformSecret(ENCRYPTION_KEY), ChannelSecret(OTHER_TELEGRAM_BOT_TOKEN)
        )
        for payload, credential in (
            (ChannelWebhookPayload(body=b"{}"), token),
            (
                ChannelWebhookPayload(
                    body=b"{}",
                    signature_header=WebhookSignatureHeader(str(other_bot_secret)),
                ),
                token,
            ),
            (valid, None),
        ):
            with pytest.raises(AuthenticationRequiredError):
                adapter.verify_signature(payload, credential)
