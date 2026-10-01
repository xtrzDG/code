from typing import Any

import httpx
import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels import ChannelWebhookPayload
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
from app.utilities.channels.channel_endpoints import TELEGRAM_SECRET_HEADER
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.channels.testbed import (
    ENCRYPTION_KEY,
    OTHER_TELEGRAM_BOT_TOKEN,
    TELEGRAM_BOT_TOKEN,
    ChannelsTestbed,
    HttpResponse,
    telegram_ok,
    to_json_bytes,
)

BOT_SECRET: str = str(
    derive_telegram_webhook_secret(
        PlatformSecret(ENCRYPTION_KEY), ChannelSecret(TELEGRAM_BOT_TOKEN)
    )
)


def build_update(
    text: str | None = "Do you have a table for 4 tonight?",
    chat_id: int = 555_000_111,
    chat_type: str = "private",
    message_id: int = 17,
    contact: dict[str, Any] | None = None,
    is_bot: bool = False,
    language_code: str = "ka",
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "message_id": message_id,
        "date": 1_790_856_000,
        "chat": {"id": chat_id, "type": chat_type},
        "from": {
            "id": chat_id,
            "is_bot": is_bot,
            "first_name": "ნინო",
            "last_name": "Beridze",
            "language_code": language_code,
        },
    }
    if text is not None:
        message["text"] = text
    if contact is not None:
        message["contact"] = contact
    return {"update_id": 1001, "message": message}


def connect_bot(testbed: ChannelsTestbed) -> tuple[BusinessDocument, ChannelDocument]:
    owner_id = testbed.add_user("owner")
    business = testbed.add_business(owner_id)
    channel = testbed.add_channel(
        business.id, ChannelKind.TELEGRAM, "funicular_vr_bot", TELEGRAM_BOT_TOKEN
    )
    testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))
    return business, channel


def post_update(
    testbed: ChannelsTestbed,
    channel: ChannelDocument,
    update: dict[str, Any],
    secret: str | None = BOT_SECRET,
) -> HttpResponse:
    headers: dict[str, str] = {} if secret is None else {TELEGRAM_SECRET_HEADER: secret}
    return testbed.build_http_client().post(
        f"/v1/channels/telegram/{channel.id}/webhook",
        content=to_json_bytes(update),
        headers=headers,
    )


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
            "allowed_updates": ["message"],
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
        messages = testbed.telegram_adapter.parse_webhook(
            self.payload(build_update(text=None, contact=friend))
        )
        assert messages == []

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


class TestTelegramWebhook:
    def test_message_is_answered_through_the_business_bot(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)

        response = post_update(testbed, channel, build_update())

        assert response.status_code == 200
        assert response.json() == {
            "received": 1,
            "answered": 1,
            "silenced": 0,
            "failed": 0,
        }
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

        sent = testbed.telegram_transport.requests_to("/sendMessage")
        assert len(sent) == 2
        assert all(len(request.json()["text"]) <= 4096 for request in sent)

    def test_assistant_stays_silent_while_staff_handle_the_chat(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.pipeline.is_silent = True

        response = post_update(testbed, channel, build_update())

        assert response.json()["silenced"] == 1
        assert testbed.telegram_transport.requests_to("/sendMessage") == []

    def test_repeated_delivery_is_answered_once(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)

        post_update(testbed, channel, build_update())
        second = post_update(testbed, channel, build_update())

        assert second.json()["received"] == 0
        assert len(testbed.pipeline.messages) == 1

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

    def test_engine_and_delivery_failures_are_counted_not_raised(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.pipeline.failure = ExternalServiceError("model unavailable")

        response = post_update(testbed, channel, build_update())

        assert response.status_code == 200
        assert response.json()["failed"] == 1

        testbed.pipeline.failure = None
        testbed.telegram_transport.respond(
            "POST",
            r"/sendMessage$",
            {"ok": False, "error_code": 403, "description": "blocked"},
            status_code=403,
        )
        response = post_update(testbed, channel, build_update(message_id=18))
        assert response.json() == {
            "received": 1,
            "answered": 0,
            "silenced": 0,
            "failed": 1,
        }
