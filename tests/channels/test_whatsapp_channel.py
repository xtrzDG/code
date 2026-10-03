"""The WhatsApp channel adapter: reading webhook messages and sending replies."""

from typing import Any

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelWebhookPayload,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
)
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    WebhookSignatureHeader,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from tests.channels.channels_payloads import sign_meta, to_json_bytes
from tests.channels.channels_settings import WHATSAPP_SYSTEM_TOKEN, build_settings
from tests.channels.meta_payloads import (
    PHONE_NUMBER_ID,
    whatsapp_message,
    whatsapp_webhook,
)
from tests.channels.testbed import ChannelsTestbed


class TestWhatsAppParsing:
    def parse(self, payload: dict[str, Any]) -> list[Any]:
        return ChannelsTestbed().whatsapp_adapter.parse_webhook(
            ChannelWebhookPayload(body=to_json_bytes(payload))
        )

    @pytest.mark.parametrize(
        ("wa_id", "expected_phone"),
        [
            ("995599123456", "+995599123456"),
            ("37477123456", "+37477123456"),
            ("972502345678", "+972502345678"),
            ("77710009998", "+77710009998"),
            ("48512345678", "+48512345678"),
            ("12025550123", "+12025550123"),
            ("5511961234567", "+5511961234567"),
            ("551187654321", "+5511987654321"),
        ],
    )
    def test_customer_numbers_of_many_countries(
        self, wa_id: str, expected_phone: str
    ) -> None:
        [message] = self.parse(
            whatsapp_webhook(
                [whatsapp_message(wa_id)],
                contacts=[{"profile": {"name": "Ana"}, "wa_id": wa_id}],
            )
        )

        assert message.channel is ChannelKind.WHATSAPP
        assert message.account_id == PHONE_NUMBER_ID
        assert message.channel_user_id == wa_id
        assert message.contact_phone_number == expected_phone
        assert message.contact_name == "Ana"
        assert message.provider_message_id == "wamid.1"

    def test_invalid_number_still_gives_the_message(self) -> None:
        [message] = self.parse(whatsapp_webhook([whatsapp_message("123")]))
        assert message.contact_phone_number is None
        assert message.channel_user_id == "123"

    def test_buttons_and_interactive_replies_are_text(self) -> None:
        messages = self.parse(
            whatsapp_webhook(
                [
                    whatsapp_message(
                        "995599123456",
                        message_type="button",
                        message_id="wamid.b",
                        extra={"button": {"text": "Confirm", "payload": "OK"}},
                    ),
                    whatsapp_message(
                        "995599123456",
                        message_type="interactive",
                        message_id="wamid.i",
                        extra={
                            "interactive": {
                                "type": "list_reply",
                                "list_reply": {"id": "1", "title": "19:00"},
                            }
                        },
                    ),
                ]
            )
        )
        assert [message.text for message in messages] == ["Confirm", "19:00"]

    def test_media_statuses_and_other_objects_are_skipped(self) -> None:
        image = whatsapp_message("995599123456", message_type="image")
        assert self.parse(whatsapp_webhook([image])) == []
        assert (
            self.parse(
                whatsapp_webhook([], statuses=[{"id": "wamid.1", "status": "read"}])
            )
            == []
        )
        assert self.parse({"object": "page", "entry": []}) == []
        assert self.parse({"object": "whatsapp_business_account", "entry": "x"}) == []

    def test_signature_uses_the_app_secret(self) -> None:
        adapter = ChannelsTestbed().whatsapp_adapter
        body = b'{"object":"whatsapp_business_account"}'
        adapter.verify_signature(
            ChannelWebhookPayload(
                body=body, signature_header=WebhookSignatureHeader(sign_meta(body))
            ),
            None,
        )
        with pytest.raises(AuthenticationRequiredError):
            adapter.verify_signature(
                ChannelWebhookPayload(
                    body=body,
                    signature_header=WebhookSignatureHeader(sign_meta(body, "x")),
                ),
                None,
            )

        unconfigured = ChannelsTestbed(
            build_settings(META_APP_SECRET="")
        ).whatsapp_adapter
        with pytest.raises(AuthenticationRequiredError):
            unconfigured.verify_signature(
                ChannelWebhookPayload(
                    body=body, signature_header=WebhookSignatureHeader(sign_meta(body))
                ),
                None,
            )


class TestWhatsAppSending:
    def target(self) -> ChannelDeliveryTarget:
        return ChannelDeliveryTarget(
            channel=ChannelKind.WHATSAPP,
            account_id=ChannelExternalId(PHONE_NUMBER_ID),
            channel_user_id=ChannelUserId("995599123456"),
        )

    def test_text_goes_through_the_cloud_api_with_the_system_token(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond(
            "POST", r"/messages$", {"messages": [{"id": "w"}]}
        )

        delivered = testbed.whatsapp_adapter.send(self.target(), MessageText("שלום"))

        assert delivered.delivered == 1
        [request] = testbed.meta_transport.requests
        assert request.path == f"/v23.0/{PHONE_NUMBER_ID}/messages"
        assert request.headers["Authorization"] == f"Bearer {WHATSAPP_SYSTEM_TOKEN}"
        assert WHATSAPP_SYSTEM_TOKEN not in str(request.url)
        assert request.json() == {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": "995599123456",
            "type": "text",
            "text": {"preview_url": False, "body": "שלום"},
        }

    def test_template_for_messages_outside_the_24_hour_window(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})

        testbed.whatsapp_adapter.send_template(
            MetaObjectId(PHONE_NUMBER_ID),
            ChannelUserId("5511961234567"),
            WhatsAppTemplateName("booking_reminder"),
            WhatsAppTemplateLanguageCode("pt_BR"),
            [MessageText("Funicular VR"), MessageText("x" * 2000)],
        )

        body = testbed.meta_transport.requests[0].json()
        assert body["type"] == "template"
        assert body["template"]["name"] == "booking_reminder"
        assert body["template"]["language"] == {"code": "pt_BR"}
        parameters = body["template"]["components"][0]["parameters"]
        assert parameters[0] == {"type": "text", "text": "Funicular VR"}
        assert len(parameters[1]["text"]) == 1024
        assert parameters[1]["text"].endswith("…")

    def test_errors_and_missing_configuration(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond(
            "POST",
            r"/messages$",
            {"error": {"message": "Re-engagement message", "code": 131047}},
            status_code=400,
        )
        with pytest.raises(ExternalServiceError, match="131047"):
            testbed.whatsapp_adapter.send(self.target(), MessageText("Hello"))

        unconfigured = ChannelsTestbed(build_settings(WHATSAPP_SYSTEM_USER_TOKEN=""))
        with pytest.raises(ExternalServiceError, match="WHATSAPP_SYSTEM_USER_TOKEN"):
            unconfigured.whatsapp_adapter.send(self.target(), MessageText("Hello"))

        broken_target = self.target().model_copy(update={"account_id": None})
        with pytest.raises(ExternalServiceError):
            testbed.whatsapp_adapter.send(broken_target, MessageText("Hello"))
