"""
Live smoke against the providers' sandboxes (nightly, contracts-live.yml):
one small call each, through the platform's real client where it has one,
and the provider's real answer checked against the vendored specification
the offline contract tests use - so drift at a provider fails here before
it reaches production. Runs only with CONTRACTS_LIVE=1; a provider without
its sandbox secrets is skipped (tests/contracts/README.md lists them).
Never give these production credentials.
"""

from typing import Any, cast
from urllib.parse import parse_qsl

import httpx
import pytest

from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.clients.flitt.flitt_client import FlittClient
from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.clients.meta.meta_graph_client import DEFAULT_GRAPH_API_VERSION
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.clients.twilio.twilio_messaging_client import TwilioMessagingClient
from app.schemas.typings.bookings.constrained_strings import CalendarRedirectUrl
from app.schemas.typings.bookings.strings import CalendarRefreshToken
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.constrained_strings import (
    SmsSenderId,
    TwilioAccountSid,
)
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from tests.billing.billing_settings import APP_BASE_URL, FLITT_MERCHANT_ID
from tests.contracts.flitt.flitt_signing import TEST_SECRET, opened
from tests.contracts.flitt.test_flitt_requests import checkout_request
from tests.contracts.live.live_network import (
    TIMEOUT_SECONDS,
    RecordingNetwork,
    checked_answer,
    is_live,
    sandbox_secrets,
)
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

pytestmark = pytest.mark.skipif(
    not is_live(), reason="The live smoke runs nightly with CONTRACTS_LIVE=1."
)
# Twilio's test credentials: this sender always succeeds and nothing is sent.
TWILIO_MAGIC_SENDER: str = "+15005550006"
TWILIO_ANY_RECIPIENT: str = "+14108675310"
ANTHROPIC_API_VERSION: str = "2023-06-01"


@pytest.fixture
def network() -> RecordingNetwork:
    return RecordingNetwork()


def json_of(content: bytes) -> Any:
    return httpx.Response(200, content=content).json()


def test_telegram_bot_profile(network: RecordingNetwork) -> None:
    [token] = sandbox_secrets("CONTRACTS_TELEGRAM_BOT_TOKEN")

    TelegramBotClient(transport=network).get_me(PlatformSecret(token))

    _, response = network.last()
    answer = cast(dict[str, Any], checked_answer(response))
    assert_inbound(answer["result"], "telegram_bot_api.json", "User")


def test_whatsapp_sandbox_message(network: RecordingNetwork) -> None:
    token, phone_number_id, recipient = sandbox_secrets(
        "CONTRACTS_META_ACCESS_TOKEN",
        "CONTRACTS_META_PHONE_NUMBER_ID",
        "CONTRACTS_META_TEST_RECIPIENT",
    )
    body: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"body": "Nightly contract check."},
    }
    assert_outbound(body, "meta_whatsapp_cloud_api.json", "request:messages.send")

    with httpx.Client(transport=network, timeout=TIMEOUT_SECONDS) as http:
        response = http.post(
            f"https://graph.facebook.com/{DEFAULT_GRAPH_API_VERSION}"
            f"/{phone_number_id}/messages",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert_inbound(
        checked_answer(response),
        "meta_whatsapp_cloud_api.json",
        "MessageResponsePayload",
    )


def test_twilio_test_credentials(network: RecordingNetwork) -> None:
    account_sid, auth_token = sandbox_secrets(
        "CONTRACTS_TWILIO_TEST_ACCOUNT_SID", "CONTRACTS_TWILIO_TEST_AUTH_TOKEN"
    )
    client = TwilioMessagingClient(
        account_sid=TwilioAccountSid(account_sid),
        auth_token=PlatformSecret(auth_token),
        sender=SmsSenderId(TWILIO_MAGIC_SENDER),
        messaging_service_sid=None,
        transport=network,
    )

    client.send_sms(
        E164PhoneNumber(TWILIO_ANY_RECIPIENT), SmsMessageText("Nightly check.")
    )

    request, response = network.last()
    form: dict[str, str] = dict(parse_qsl(request.content.decode()))
    assert_outbound(form, "twilio_messaging_api.json", "request:messages.create")
    assert_inbound(
        checked_answer(response),
        "twilio_messaging_api.json",
        "response:messages.create",
    )


def test_flitt_test_merchant_checkout(network: RecordingNetwork) -> None:
    # Flitt's documented test merchant: public credentials, no secrets.
    gateway = FlittPaymentGatewayAdapter(
        flitt_client=FlittClient(
            merchant_id=PlatformIdentifier(FLITT_MERCHANT_ID),
            secret_key=PlatformSecret(TEST_SECRET),
            transport=network,
        ),
        app_base_url=PublicBaseUrl(APP_BASE_URL),
    )

    gateway.create_checkout(checkout_request())

    request, response = network.last()
    sent: dict[str, Any] = json_of(request.content)
    assert_outbound(sent, "flitt_api.json", "request:api")
    assert_outbound(opened(sent), "flitt_api.json", "CheckoutOrder")
    assert_inbound(checked_answer(response), "flitt_api.json", "response:api")


def test_google_calendar_list(network: RecordingNetwork) -> None:
    client_id, client_secret, refresh_token = sandbox_secrets(
        "CONTRACTS_GOOGLE_CLIENT_ID",
        "CONTRACTS_GOOGLE_CLIENT_SECRET",
        "CONTRACTS_GOOGLE_REFRESH_TOKEN",
    )
    google = GoogleCalendarClient(
        client_id=PlatformIdentifier(client_id),
        client_secret=PlatformSecret(client_secret),
        redirect_url=CalendarRedirectUrl("https://api.example.com/v1/google"),
        transport=network,
    )

    grant = google.refresh_access_token(CalendarRefreshToken(refresh_token))
    google.list_calendars(grant.access_token, BusyTimeFetchSeconds(10.0))

    _, response = network.last()
    assert_inbound(checked_answer(response), "google_calendar_api.json", "CalendarList")


def test_openai_response(network: RecordingNetwork) -> None:
    [api_key] = sandbox_secrets("CONTRACTS_OPENAI_API_KEY")
    body: dict[str, Any] = {
        "model": "gpt-5-mini",
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": "Answer with: ok"}],
            }
        ],
        "max_output_tokens": 64,
        "store": False,
    }
    assert_outbound(body, "openai_responses_api.json", "request:responses.create")

    with httpx.Client(transport=network, timeout=TIMEOUT_SECONDS) as http:
        response = http.post(
            "https://api.openai.com/v1/responses",
            json=body,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    assert_inbound(checked_answer(response), "openai_responses_api.json", "Response")


def test_anthropic_message(network: RecordingNetwork) -> None:
    [api_key] = sandbox_secrets("CONTRACTS_ANTHROPIC_API_KEY")
    body: dict[str, Any] = {
        "model": "claude-sonnet-5-5",
        "max_tokens": 16,
        "messages": [{"role": "user", "content": [{"type": "text", "text": "ok?"}]}],
    }
    assert_outbound(body, "anthropic_messages_api.json", "request:messages.create")

    with httpx.Client(transport=network, timeout=TIMEOUT_SECONDS) as http:
        response = http.post(
            "https://api.anthropic.com/v1/messages",
            json=body,
            headers={"x-api-key": api_key, "anthropic-version": ANTHROPIC_API_VERSION},
        )

    assert_inbound(
        checked_answer(response),
        "anthropic_messages_api.json",
        "response:messages.create",
    )


def test_elevenlabs_conversation(network: RecordingNetwork) -> None:
    [api_key] = sandbox_secrets("CONTRACTS_ELEVENLABS_API_KEY")

    with httpx.Client(
        transport=network,
        timeout=TIMEOUT_SECONDS,
        base_url="https://api.elevenlabs.io/v1/convai",
        headers={"xi-api-key": api_key},
    ) as http:
        page = cast(
            dict[str, Any],
            checked_answer(http.get("/conversations", params={"page_size": 1})),
        )
        if not page["conversations"]:
            pytest.skip("The sandbox workspace has no conversation yet.")
        conversation_id: str = page["conversations"][0]["conversation_id"]
        response = http.get(f"/conversations/{conversation_id}")

    assert_inbound(
        checked_answer(response), "elevenlabs_agents_api.json", "Conversation"
    )
