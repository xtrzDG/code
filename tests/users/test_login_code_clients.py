"""HTTP clients of the login code providers: request shape and error mapping."""

import base64
import logging

import httpx
import pytest

from app.clients.meta.whatsapp_authentication_client import (
    WhatsAppAuthenticationClient,
)
from app.clients.telegram.telegram_gateway_client import TelegramGatewayClient
from app.clients.twilio.twilio_messaging_client import TwilioMessagingClient
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.constrained_strings import (
    SmsSenderId,
    TwilioAccountSid,
    TwilioMessagingServiceSid,
)
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_integers import OtpLifetimeSeconds
from app.schemas.typings.users.constrained_strings import OtpCode
from tests.users.login_code_http import ScriptedProvider, json_response

ACCOUNT_SID = TwilioAccountSid("AC" + "1f" * 16)
AUTH_TOKEN = PlatformSecret("twilio-auth-token-secret")
SERVICE_SID = TwilioMessagingServiceSid("MG" + "2e" * 16)
GATEWAY_TOKEN = PlatformSecret("AAGateway-token-secret")
META_TOKEN = PlatformSecret("EAAG-meta-token-secret")
PHONE = E164PhoneNumber("+995555123456")
CODE = OtpCode("042317")
SENDER = SmsSenderId("+12025550123")
SECRETS: tuple[str, ...] = (str(AUTH_TOKEN), str(GATEWAY_TOKEN), str(META_TOKEN))


def assert_no_secrets(text: str) -> None:
    for secret in SECRETS:
        assert secret not in text


class TestTwilioMessagingClient:
    def build(
        self,
        provider: ScriptedProvider,
        sender: SmsSenderId | None = SENDER,
        service_sid: TwilioMessagingServiceSid | None = None,
    ) -> TwilioMessagingClient:
        return TwilioMessagingClient(
            account_sid=ACCOUNT_SID,
            auth_token=AUTH_TOKEN,
            sender=sender,
            messaging_service_sid=service_sid,
            transport=provider.transport(),
        )

    def test_sms_is_posted_as_a_form_with_basic_auth(self) -> None:
        provider = ScriptedProvider(
            json_response(201, {"sid": "SM1", "status": "queued"})
        )

        self.build(provider).send_sms(PHONE, SmsMessageText("Code: 042317"))

        request = provider.last
        assert request.method == "POST"
        assert request.url == (
            f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages.json"
        )
        assert request.headers["content-type"] == "application/x-www-form-urlencoded"
        expected_credentials = base64.b64encode(
            f"{ACCOUNT_SID}:{AUTH_TOKEN}".encode()
        ).decode()
        assert request.headers["authorization"] == f"Basic {expected_credentials}"
        assert provider.form_body() == {
            "To": ["+995555123456"],
            "Body": ["Code: 042317"],
            "From": ["+12025550123"],
        }

    def test_messaging_service_replaces_the_sender_number(self) -> None:
        provider = ScriptedProvider(json_response(201, {"sid": "SM1"}))

        self.build(provider, sender=None, service_sid=SERVICE_SID).send_sms(
            PHONE, SmsMessageText("Code")
        )

        form = provider.form_body()
        assert form["MessagingServiceSid"] == [str(SERVICE_SID)]
        assert "From" not in form

    def test_a_sender_is_required(self) -> None:
        with pytest.raises(ValueError, match="sender"):
            self.build(ScriptedProvider(json_response(201, {})), sender=None)

    @pytest.mark.parametrize(
        ("response", "expected"),
        [
            (
                json_response(
                    400,
                    {
                        "code": 21211,
                        "message": "The 'To' number +995555123456 is not valid.",
                        "status": 400,
                    },
                ),
                r"HTTP 400, error 21211",
            ),
            (json_response(401, {"code": 20003}), "TWILIO_AUTH_TOKEN"),
            (httpx.Response(503, content=b"<html>down</html>"), r"HTTP 503\)"),
        ],
    )
    def test_refusals_name_the_error_code_only(
        self,
        response: httpx.Response,
        expected: str,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        client = self.build(ScriptedProvider(response))

        with (
            caplog.at_level(logging.DEBUG),
            pytest.raises(ExternalServiceError, match=expected) as raised,
        ):
            client.send_sms(PHONE, SmsMessageText("Code: 042317"))

        message = str(raised.value)
        assert "+995555123456" not in message
        assert "042317" not in message
        assert_no_secrets(message + caplog.text)
        assert raised.value.__cause__ is None

    def test_transport_errors_are_external_errors(self) -> None:
        client = self.build(ScriptedProvider(httpx.ConnectError("refused")))

        with pytest.raises(ExternalServiceError, match="ConnectError"):
            client.send_sms(PHONE, SmsMessageText("Code"))


class TestTelegramGatewayClient:
    def test_code_is_sent_with_bearer_token_and_ttl(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        provider = ScriptedProvider(
            json_response(200, {"ok": True, "result": {"request_id": "r1"}})
        )
        client = TelegramGatewayClient(GATEWAY_TOKEN, transport=provider.transport())

        with caplog.at_level(logging.DEBUG):
            client.send_verification_message(PHONE, CODE, OtpLifetimeSeconds(600))

        assert provider.last.url == (
            "https://gatewayapi.telegram.org/sendVerificationMessage"
        )
        assert provider.last.headers["authorization"] == f"Bearer {GATEWAY_TOKEN}"
        assert provider.json_body() == {
            "phone_number": "+995555123456",
            "code": "042317",
            "ttl": 600,
        }
        assert_no_secrets(caplog.text)

    @pytest.mark.parametrize(
        ("response", "expected"),
        [
            (
                json_response(200, {"ok": False, "error": "PHONE_NUMBER_INVALID"}),
                "PHONE_NUMBER_INVALID",
            ),
            (
                json_response(401, {"ok": False, "error": "ACCESS_TOKEN_INVALID"}),
                "ACCESS_TOKEN_INVALID",
            ),
            (
                json_response(400, {"ok": False, "error": "token AAGateway-token"}),
                "HTTP 400",
            ),
            (httpx.Response(502, content=b"bad gateway"), "without a JSON body"),
        ],
    )
    def test_refusals_are_external_errors(
        self, response: httpx.Response, expected: str
    ) -> None:
        client = TelegramGatewayClient(
            GATEWAY_TOKEN, transport=ScriptedProvider(response).transport()
        )

        with pytest.raises(ExternalServiceError, match=expected) as raised:
            client.send_verification_message(PHONE, CODE, OtpLifetimeSeconds(300))

        assert_no_secrets(str(raised.value))
        assert "AAGateway" not in str(raised.value)


class TestWhatsAppAuthenticationClient:
    def build(self, provider: ScriptedProvider) -> WhatsAppAuthenticationClient:
        return WhatsAppAuthenticationClient(
            access_token=META_TOKEN,
            phone_number_id=MetaObjectId("106540352242922"),
            template_name=WhatsAppTemplateName("login_code"),
            transport=provider.transport(),
        )

    def test_authentication_template_carries_the_code_twice(self) -> None:
        provider = ScriptedProvider(
            json_response(200, {"messages": [{"id": "wamid.1"}]})
        )

        self.build(provider).send_authentication_code(
            PHONE, CODE, WhatsAppTemplateLanguageCode("ka")
        )

        assert provider.last.url == (
            "https://graph.facebook.com/v23.0/106540352242922/messages"
        )
        assert provider.last.headers["authorization"] == f"Bearer {META_TOKEN}"
        assert provider.json_body() == {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": "995555123456",
            "type": "template",
            "template": {
                "name": "login_code",
                "language": {"code": "ka"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": "042317"}],
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [{"type": "text", "text": "042317"}],
                    },
                ],
            },
        }

    @pytest.mark.parametrize(
        ("response", "expected"),
        [
            (
                json_response(
                    400,
                    {
                        "error": {
                            "code": 132001,
                            "message": "Template name does not exist",
                        }
                    },
                ),
                "132001.*does not exist in this language",
            ),
            (
                json_response(401, {"error": {"code": 190, "message": "bad token"}}),
                "190.*access token",
            ),
            (
                json_response(400, {"error": {"code": 131999, "message": "x"}}),
                "error 131999",
            ),
            (httpx.Response(500, content=b""), r"HTTP 500"),
        ],
    )
    def test_refusals_are_external_errors(
        self, response: httpx.Response, expected: str
    ) -> None:
        client = self.build(ScriptedProvider(response))

        with pytest.raises(ExternalServiceError, match=expected) as raised:
            client.send_authentication_code(
                PHONE, CODE, WhatsAppTemplateLanguageCode("en")
            )

        assert "042317" not in str(raised.value)
        assert_no_secrets(str(raised.value))

    def test_transport_errors_are_external_errors(self) -> None:
        client = self.build(ScriptedProvider(httpx.ReadTimeout("slow")))

        with pytest.raises(ExternalServiceError, match="ReadTimeout"):
            client.send_authentication_code(
                PHONE, CODE, WhatsAppTemplateLanguageCode("en")
            )
