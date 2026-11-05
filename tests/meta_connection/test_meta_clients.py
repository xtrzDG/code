"""Meta's sign-in, pages, onboarding and private-reply clients over mock transports."""

import httpx
import pytest

from app.clients.meta.meta_oauth_client import MetaOAuthClient
from app.clients.meta.meta_pages_client import MetaPagesClient
from app.clients.meta.meta_private_reply_client import MetaPrivateReplyClient
from app.clients.meta.whatsapp_onboarding_client import WhatsAppOnboardingClient
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
    ProviderRejectedMessageError,
    ValidationFailedError,
)
from app.schemas.exceptions.meta_connection_errors import WhatsAppPinMismatchError
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaCommentId,
    MetaEmbeddedSignupCode,
    MetaPermissionName,
    WhatsAppBusinessAccountId,
    WhatsAppRegistrationPin,
)
from app.schemas.typings.meta_connection.strings import MetaAccessToken
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from tests.channels.recording_transport import RecordingTransport

APP = MetaAppCredentials(
    app_id=PlatformIdentifier("1234567890"),
    app_secret=PlatformSecret("test-app-secret-0000"),
)
TOKEN = MetaAccessToken("test-business-token-0000")
CODE = MetaEmbeddedSignupCode("AQB-test-code-0000-0000")
WABA = WhatsAppBusinessAccountId("102290129340398")


def refused(code: int, status: int = 400) -> dict[str, object]:
    return {"error": {"message": "Refused", "type": "OAuthException", "code": code}}


def failing_transport() -> httpx.MockTransport:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    return httpx.MockTransport(fail)


class TestOAuthClient:
    def test_codes_become_tokens_and_bad_codes_are_refused(self) -> None:
        graph = RecordingTransport()
        client = MetaOAuthClient(transport=graph.build())
        graph.respond("GET", r"/oauth/access_token$", {"access_token": "t-0000"})

        assert client.exchange_code(CODE, APP) == "t-0000"
        assert graph.requests[0].url.params["client_secret"] == "test-app-secret-0000"
        assert "Authorization" not in graph.requests[0].headers

        graph.respond("GET", r"/oauth/access_token$", refused(100), status_code=400)
        with pytest.raises(ValidationFailedError):
            client.exchange_code(CODE, APP)

        graph.respond("GET", r"/oauth/access_token$", {"token_type": "bearer"})
        with pytest.raises(ExternalServiceError):
            client.extend_user_token(TOKEN, APP)

    def test_grants_read_granular_targets(self) -> None:
        graph = RecordingTransport()
        client = MetaOAuthClient(transport=graph.build())
        graph.respond(
            "GET",
            r"/debug_token$",
            {
                "data": {
                    "is_valid": True,
                    "scopes": ["pages_show_list", "whatsapp_business_management"],
                    "granular_scopes": [
                        {
                            "scope": "whatsapp_business_management",
                            "target_ids": [str(WABA), "not-an-id"],
                        },
                        {"scope": "whatsapp_business_messaging"},
                        {"target_ids": ["1"]},
                    ],
                }
            },
        )

        grants = client.read_grants(TOKEN, APP)

        management = MetaPermissionName("whatsapp_business_management")
        assert grants.targets_of(management) == [MetaObjectId(str(WABA))]
        assert grants.has(MetaPermissionName("whatsapp_business_messaging"))
        assert grants.has(MetaPermissionName("pages_show_list"))
        assert grants.targets_of(MetaPermissionName("pages_show_list")) == []

    def test_an_invalid_token_and_an_unreachable_meta(self) -> None:
        graph = RecordingTransport()
        graph.respond("GET", r"/debug_token$", {"data": {"is_valid": False}})

        with pytest.raises(ValidationFailedError):
            MetaOAuthClient(transport=graph.build()).read_grants(TOKEN, APP)
        with pytest.raises(ExternalServiceError):
            MetaOAuthClient(transport=failing_transport()).exchange_code(CODE, APP)


class TestPagesClient:
    def test_a_page_without_a_token_is_not_offered(self) -> None:
        graph = RecordingTransport()
        graph.respond("GET", r"/4410001$", {"id": "4410001"})
        graph.respond("GET", r"/me/accounts$", {"data": [{"name": "no id"}]})
        client = MetaPagesClient(transport=graph.build())

        assert client.read_page_token(TOKEN, MetaObjectId("4410001"), APP) is None
        assert client.list_pages(TOKEN, APP) == []


class TestOnboardingClient:
    def test_numbers_subscription_and_registration(self) -> None:
        graph = RecordingTransport()
        graph.respond(
            "GET",
            rf"/{WABA}/phone_numbers$",
            {"data": [{"id": "106540352242923"}, {"id": "x"}]},
        )
        graph.respond("POST", rf"/{WABA}/subscribed_apps$", {"success": True})
        graph.respond("POST", r"/106540352242923/register$", {"success": True})
        client = WhatsAppOnboardingClient(transport=graph.build())

        numbers = client.list_phone_numbers(TOKEN, WABA, APP)
        client.subscribe_app(TOKEN, WABA, APP)
        client.register_number(
            TOKEN, numbers[0].phone_number_id, WhatsAppRegistrationPin("482913"), APP
        )

        assert [str(number.phone_number_id) for number in numbers] == [
            "106540352242923"
        ]
        assert numbers[0].display_phone_number is None
        assert graph.requests[-1].json() == {
            "messaging_product": "whatsapp",
            "pin": "482913",
        }

    def test_registration_refusals(self) -> None:
        graph = RecordingTransport()
        client = WhatsAppOnboardingClient(transport=graph.build())
        number = MetaObjectId("106540352242923")
        pin = WhatsAppRegistrationPin("482913")

        graph.respond("POST", r"/register$", refused(133005), status_code=400)
        with pytest.raises(WhatsAppPinMismatchError):
            client.register_number(TOKEN, number, pin, APP)

        graph.respond("POST", r"/register$", refused(190), status_code=401)
        with pytest.raises(ChannelCredentialRejectedError):
            client.register_number(TOKEN, number, pin, APP)

        with pytest.raises(ExternalServiceError):
            WhatsAppOnboardingClient(transport=failing_transport()).register_number(
                TOKEN, number, pin, APP
            )


class TestPrivateReplyClient:
    def test_the_reply_names_the_comment(self) -> None:
        graph = RecordingTransport()
        graph.respond("POST", r"/me/messages$", {"message_id": "mid.9"})
        client = MetaPrivateReplyClient(transport=graph.build())

        sent = client.send_private_reply(
            ChannelSecret("test-page-token-0000"),
            MetaCommentId("17858893269000001"),
            MessageText("Hi"),
        )

        assert sent == "mid.9"
        assert graph.requests[0].json() == {
            "recipient": {"comment_id": "17858893269000001"},
            "message": {"text": "Hi"},
        }

    def test_an_answered_comment_is_refused_for_good(self) -> None:
        graph = RecordingTransport()
        graph.respond("POST", r"/me/messages$", refused(10903), status_code=400)
        graph.respond("POST", r"/me/messages$", refused(10903), status_code=400)

        with pytest.raises(ProviderRejectedMessageError):
            MetaPrivateReplyClient(transport=graph.build()).send_private_reply(
                ChannelSecret("test-page-token-0000"),
                MetaCommentId("17858893269000001"),
                MessageText("Hi"),
            )
