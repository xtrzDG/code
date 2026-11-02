"""
The providers' webhooks are admitted before their bodies are read: an
unsigned or malformed signature is refused at once (401, Stripe 403), a
flood from one client network gets 429 with Retry-After, and each refusal
is a security log line without personal data.
"""

import logging

import pytest
from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient

from app.gateways.http.application import build_http_application
from app.gateways.http.middleware.webhook_admission_middleware import (
    WebhookAdmissionMiddleware,
)
from app.gateways.http.middleware.webhook_deliveries import (
    WEBHOOK_ROUTES,
    find_webhook_route,
)
from app.utilities.observability.security_events import (
    RATE_LIMIT_TRIGGERED,
    WEBHOOK_DELIVERY_REFUSED,
)

HEX: str = "ab" * 32
BODY_READS: list[str] = []
SIGNED: dict[str, dict[str, str]] = {
    "/v1/channels/telegram/channel_1/webhook": {"X-Telegram-Bot-Api-Secret-Token": HEX},
    "/v1/channels/telegram-platform/webhook": {"X-Telegram-Bot-Api-Secret-Token": HEX},
    "/v1/channels/meta/webhook": {"X-Hub-Signature-256": f"sha256={HEX}"},
    "/v1/voice/webhooks/post-call": {"ElevenLabs-Signature": f"t=1790000000,v0={HEX}"},
    "/v1/voice/webhooks/conversation-initiation": {
        "X-Assistant-Business-Id": "business_1",
        "X-Assistant-Tool-Secret": HEX,
    },
    "/v1/voice/tools/book_table": {
        "X-Assistant-Business-Id": "business_1",
        "X-Assistant-Signature": f"sha256={HEX}",
    },
    "/v1/telephony/zadarma/notifications": {"Signature": "bm90IGEgc2lnbmF0dXJl"},
    "/v1/telephony/twilio/voice-fallback/business_1": {
        "X-Twilio-Signature": "bm90IGEgc2lnbmF0dXJlIGF0IGFsbA=="
    },
    "/v1/telephony/twilio/voice-fallback/business_1/dial-status": {
        "X-Twilio-Signature": "bm90IGEgc2lnbmF0dXJlIGF0IGFsbA=="
    },
    "/v1/payments/stripe/webhook": {"Stripe-Signature": f"t=1790000000,v1={HEX}"},
    "/v1/payments/flitt/webhook": {},
}


class SilentErrorReporter:
    def capture_exception(self, error: BaseException) -> None:
        del error


def build_client(client_address: str = "198.51.100.7") -> TestClient:
    router = APIRouter()

    async def read_body(request: Request) -> dict[str, int]:
        BODY_READS.append(request.url.path)
        return {"length": len(await request.body())}

    for path in SIGNED:
        router.add_api_route(
            path.replace("channel_1", "{channel_id}"),
            read_body,
            methods=["POST", "GET"],
        )

    application = build_http_application(
        routers=[router],
        error_reporter=SilentErrorReporter(),
        cors_allowed_origins=[],
    )
    return TestClient(application, client=(client_address, 40000))


def test_every_webhook_address_is_known_to_the_admission() -> None:
    for path in SIGNED:
        assert find_webhook_route(path) is not None, path

    assert find_webhook_route("/v1/channels/meta/webhook/extra") is None
    assert find_webhook_route("/v1/businesses/b/webhooks") is None
    assert len({route.path for route in WEBHOOK_ROUTES}) == len(WEBHOOK_ROUTES)


@pytest.mark.parametrize("path", list(SIGNED))
def test_a_well_formed_delivery_reaches_its_route(path: str) -> None:
    response = build_client().post(path, content=b"{}", headers=SIGNED[path])

    assert response.status_code == 200, response.text
    assert response.json() == {"length": 2}


@pytest.mark.parametrize("path", [path for path, headers in SIGNED.items() if headers])
def test_an_unsigned_delivery_is_refused_before_its_body_is_read(
    path: str, caplog: pytest.LogCaptureFixture
) -> None:
    BODY_READS.clear()
    caplog.set_level(logging.WARNING, logger="app.security")

    response = build_client().post(path, content=b'{"x": 1}')

    expected: int = 403 if "stripe" in path else 401
    assert response.status_code == expected
    assert response.json()["error"] in {"authentication_required", "access_denied"}
    assert BODY_READS == []
    [line] = [r for r in caplog.records if r.name == "app.security"]
    fields = getattr(line, "log_fields")
    assert fields["security_event"] == WEBHOOK_DELIVERY_REFUSED
    assert fields["reason"] == "missing_signature"
    assert fields["client_network"] == "198.51.100.0/24"
    assert "198.51.100.7" not in line.getMessage()


@pytest.mark.parametrize(
    ("path", "headers"),
    [
        ("/v1/channels/meta/webhook", {"X-Hub-Signature-256": "sha256=00"}),
        ("/v1/channels/meta/webhook", {"X-Hub-Signature-256": HEX}),
        ("/v1/voice/webhooks/post-call", {"ElevenLabs-Signature": "t=abc,v0="}),
        ("/v1/voice/webhooks/post-call", {"ElevenLabs-Signature": "t=1,v0=zz"}),
        (
            "/v1/channels/telegram-platform/webhook",
            {"X-Telegram-Bot-Api-Secret-Token": "not allowed!"},
        ),
        (
            "/v1/voice/tools/book_table",
            {
                "X-Assistant-Business-Id": "business_1",
                "X-Assistant-Signature": "md5=00",
            },
        ),
        ("/v1/voice/tools/book_table", {"X-Assistant-Tool-Secret": HEX}),
        ("/v1/telephony/zadarma/notifications", {"Signature": "<script>"}),
        ("/v1/payments/stripe/webhook", {"Stripe-Signature": "t=1,v1=0000"}),
        ("/v1/payments/stripe/webhook", {"Stripe-Signature": f"v1={HEX}"}),
    ],
)
def test_a_malformed_signature_is_refused_at_once(
    path: str, headers: dict[str, str]
) -> None:
    BODY_READS.clear()

    response = build_client().post(path, content=b"{}", headers=headers)

    assert response.status_code in {401, 403}
    assert BODY_READS == []


def test_a_meta_verification_get_needs_no_signature() -> None:
    response = build_client().get("/v1/channels/meta/webhook")

    assert response.status_code == 200


def test_a_flood_from_one_network_is_held_per_provider(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger="app.security")
    now: list[float] = [0.0]
    inner = FastAPI()
    inner.add_api_route("/v1/channels/meta/webhook", accept, methods=["POST"])
    inner.add_api_route("/v1/payments/flitt/webhook", accept, methods=["POST"])
    admission = WebhookAdmissionMiddleware(
        inner, clock=lambda: now[0], per_minute={"meta": 2}
    )
    client = TestClient(admission, client=("198.51.100.7", 40000))
    neighbour = TestClient(admission, client=("203.0.113.9", 40000))
    path = "/v1/channels/meta/webhook"

    answers = [client.post(path, headers=SIGNED[path]) for _ in range(4)]
    other_network = neighbour.post(path, headers=SIGNED[path])
    other_provider = client.post("/v1/payments/flitt/webhook")
    now[0] += 30.0
    after_a_while = client.post(path, headers=SIGNED[path])

    assert [answer.status_code for answer in answers] == [200, 200, 429, 429]
    assert answers[2].json()["error"] == "rate_limited"
    assert answers[2].headers["Retry-After"] == "30"
    assert other_network.status_code == 200
    assert other_provider.status_code == 200
    assert after_a_while.status_code == 200
    floods = [
        record
        for record in caplog.records
        if getattr(record, "log_fields", {}).get("security_event")
        == RATE_LIMIT_TRIGGERED
    ]
    # One line when the flood starts, not one per refused delivery.
    assert len(floods) == 1
    assert getattr(floods[0], "log_fields")["provider"] == "meta"


async def accept() -> dict[str, str]:
    return {"accepted": "yes"}
