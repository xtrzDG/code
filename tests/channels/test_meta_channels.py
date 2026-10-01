from typing import Any

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.dto.channels import ChannelDeliveryTarget, ChannelWebhookPayload
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
    ChannelSecret,
    WebhookSignatureHeader,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.utilities.channels.channel_endpoints import META_SIGNATURE_HEADER
from tests.channels.testbed import (
    META_VERIFY_TOKEN,
    PAGE_ACCESS_TOKEN,
    WHATSAPP_SYSTEM_TOKEN,
    ChannelsTestbed,
    HttpResponse,
    build_settings,
    sign_meta,
    to_json_bytes,
)

PHONE_NUMBER_ID: str = "106540352242922"
PAGE_ID: str = "4410001"
INSTAGRAM_ID: str = "17841400000000001"


def whatsapp_message(
    sender: str,
    text: str = "Hola, ¿tienen mesa?",
    message_id: str = "wamid.1",
    message_type: str = "text",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "from": sender,
        "id": message_id,
        "timestamp": "1790856000",
        "type": message_type,
    }
    if message_type == "text":
        message["text"] = {"body": text}
    message.update(extra or {})
    return message


def whatsapp_webhook(
    messages: list[dict[str, Any]],
    phone_number_id: str = PHONE_NUMBER_ID,
    contacts: list[dict[str, Any]] | None = None,
    statuses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "metadata": {
            "display_phone_number": "+995 32 200 00 00",
            "phone_number_id": phone_number_id,
        },
        "contacts": contacts or [],
        "messages": messages,
    }
    if statuses is not None:
        value["statuses"] = statuses
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": value}]}],
    }


def page_webhook(
    object_name: str,
    account_id: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "object": object_name,
        "entry": [{"id": account_id, "time": 1790856000, "messaging": events}],
    }


def page_message(
    sender: str,
    text: str | None,
    account_id: str,
    mid: str = "mid.1",
    is_echo: bool = False,
) -> dict[str, Any]:
    message: dict[str, Any] = {"mid": mid}
    if text is not None:
        message["text"] = text
    if is_echo:
        message["is_echo"] = True
    return {
        "sender": {"id": sender},
        "recipient": {"id": account_id},
        "timestamp": 1790856000,
        "message": message,
    }


def post_meta(
    testbed: ChannelsTestbed,
    payload: dict[str, Any],
    signature: str | None = "valid",
) -> HttpResponse:
    body: bytes = to_json_bytes(payload)
    headers: dict[str, str] = {}
    if signature == "valid":
        headers[META_SIGNATURE_HEADER] = sign_meta(body)
    elif signature is not None:
        headers[META_SIGNATURE_HEADER] = signature
    return testbed.build_http_client().post(
        "/v1/channels/meta/webhook", content=body, headers=headers
    )


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

        assert delivered == 1
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

        assert delivered == 2
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


class TestMetaWebhookVerification:
    def test_challenge_is_echoed_for_the_right_token(self) -> None:
        client = ChannelsTestbed().build_http_client()
        response = client.get(
            "/v1/channels/meta/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": META_VERIFY_TOKEN,
                "hub.challenge": "1158201444",
            },
        )

        assert response.status_code == 200
        assert response.text == "1158201444"

    @pytest.mark.parametrize(
        "params",
        [
            {"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "1"},
            {
                "hub.mode": "other",
                "hub.verify_token": META_VERIFY_TOKEN,
                "hub.challenge": "1",
            },
            {"hub.mode": "subscribe", "hub.verify_token": META_VERIFY_TOKEN},
            {},
        ],
    )
    def test_wrong_verification_is_refused(self, params: dict[str, str]) -> None:
        client = ChannelsTestbed().build_http_client()
        assert client.get("/v1/channels/meta/webhook", params=params).status_code == 403


class TestMetaWebhook:
    def test_messages_are_routed_to_the_owning_business(self) -> None:
        testbed = ChannelsTestbed()
        owner_a, owner_b = testbed.add_user("a"), testbed.add_user("b")
        business_a = testbed.add_business(owner_a, name="Tbilisi Grill")
        business_b = testbed.add_business(owner_b, name="Warsaw Bistro")
        testbed.add_channel(business_a.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID)
        testbed.add_channel(business_b.id, ChannelKind.WHATSAPP, "200000000000002")
        testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})

        response = post_meta(
            testbed,
            whatsapp_webhook([whatsapp_message("48512345678", "Dzień dobry")]),
        )

        assert response.json()["answered"] == 1
        [inbound] = testbed.pipeline.messages
        assert inbound.business_id == business_a.id
        assert inbound.contact_phone_number == "+48512345678"
        [sent] = testbed.meta_transport.requests
        assert sent.path == f"/v23.0/{PHONE_NUMBER_ID}/messages"
        [usage] = testbed.usage_event_repo.list_by_business_between(
            business_a.id,
            testbed.clock.now_microseconds(),
            Microseconds(testbed.clock.now_microseconds() + 1),
        )
        assert usage.kind is UsageKind.WHATSAPP_REPLY
        assert usage.quantity == 1
        assert usage.conversation_id == testbed.pipeline.conversation_id

    def test_messages_for_unknown_or_disabled_accounts_are_dropped(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        testbed.add_channel(
            business.id,
            ChannelKind.MESSENGER,
            PAGE_ID,
            PAGE_ACCESS_TOKEN,
            status=ChannelStatus.DISABLED,
        )

        unknown = post_meta(
            testbed,
            whatsapp_webhook([whatsapp_message("995599123456")], "999"),
        )
        disabled = post_meta(
            testbed,
            page_webhook("page", PAGE_ID, [page_message("psid", "Hi", PAGE_ID)]),
        )

        assert unknown.json()["received"] == 0
        assert disabled.json()["received"] == 0
        assert testbed.pipeline.messages == []

    def test_instagram_and_messenger_use_their_page_tokens(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        testbed.add_channel(
            business.id, ChannelKind.MESSENGER, PAGE_ID, "messenger-token-0123456789"
        )
        testbed.add_channel(
            business.id, ChannelKind.INSTAGRAM, INSTAGRAM_ID, PAGE_ACCESS_TOKEN
        )
        testbed.meta_transport.respond("POST", r"/me/messages$", {"message_id": "m"})

        post_meta(
            testbed,
            page_webhook(
                "instagram", INSTAGRAM_ID, [page_message("ig-1", "Hi", INSTAGRAM_ID)]
            ),
        )
        post_meta(
            testbed,
            page_webhook(
                "page", PAGE_ID, [page_message("ps-1", "Hi", PAGE_ID, mid="m2")]
            ),
        )

        tokens = [r.headers["Authorization"] for r in testbed.meta_transport.requests]
        assert tokens == [
            f"Bearer {PAGE_ACCESS_TOKEN}",
            "Bearer messenger-token-0123456789",
        ]
        assert [m.channel for m in testbed.pipeline.messages] == [
            ChannelKind.INSTAGRAM,
            ChannelKind.MESSENGER,
        ]
        assert (
            testbed.usage_event_repo.list_by_business_between(
                business.id,
                testbed.clock.now_microseconds(),
                Microseconds(testbed.clock.now_microseconds() + 1),
            )
            == []
        )

    @pytest.mark.parametrize("signature", [None, "sha256=00", "garbage"])
    def test_unsigned_or_wrongly_signed_deliveries_are_refused(
        self, signature: str | None
    ) -> None:
        testbed = ChannelsTestbed()
        response = post_meta(
            testbed, whatsapp_webhook([whatsapp_message("1")]), signature=signature
        )
        assert response.status_code == 401

    def test_signed_unknown_objects_are_acknowledged_and_ignored(self) -> None:
        testbed = ChannelsTestbed()
        response = post_meta(testbed, {"object": "user", "entry": []})
        assert response.status_code == 200
        assert response.json()["received"] == 0
        assert post_meta(testbed, {"object": "user"}, signature=None).status_code == 401

    def test_repeated_delivery_and_staff_silence(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        testbed.add_channel(business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID)
        testbed.pipeline.is_silent = True
        payload = whatsapp_webhook([whatsapp_message("995599123456")])

        first = post_meta(testbed, payload)
        second = post_meta(testbed, payload)

        assert first.json()["silenced"] == 1
        assert second.json()["received"] == 0
        assert testbed.meta_transport.requests == []
