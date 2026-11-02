"""
Security events are structured log lines with stable names: a refused
webhook delivery, an authorization denial and a rate limit, each with the
route, the reason and the client network, never the address or a token.
"""

import logging

import pytest
from fastapi import APIRouter, Request
from fastapi.testclient import TestClient

from app.gateways.http.application import build_http_application
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    AuthenticationRequiredError,
    RateLimitedError,
)
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds
from app.utilities.observability.security_events import (
    AUTHORIZATION_DENIED,
    RATE_LIMIT_TRIGGERED,
    WEBHOOK_DELIVERY_REFUSED,
    describe_logged_network,
    log_security_event,
)

SECRET_TOKEN: str = "Bearer very-secret-token-0000"


class SilentErrorReporter:
    def capture_exception(self, error: BaseException) -> None:
        del error


def build_client(address: str = "203.0.113.77") -> TestClient:
    router = APIRouter()

    @router.get("/v1/businesses/{business_id}/secret")
    def secret(business_id: str) -> None:
        del business_id
        raise AccessDeniedError("Owners only.")

    @router.get("/v1/me")
    def me(request: Request) -> None:
        del request
        raise AuthenticationRequiredError("The session is invalid.")

    @router.post("/v1/busy")
    def busy() -> None:
        raise RateLimitedError("Too many.", retry_after_seconds=RetryAfterSeconds(5))

    @router.post("/v1/channels/meta/webhook")
    def meta() -> None:
        raise AuthenticationRequiredError("The Meta signature is wrong.")

    application = build_http_application(
        routers=[router], error_reporter=SilentErrorReporter(), cors_allowed_origins=[]
    )
    return TestClient(application, client=(address, 40000))


def security_lines(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    return [
        dict(record.__dict__["log_fields"])
        for record in caplog.records
        if record.name == "app.security"
    ]


@pytest.mark.parametrize(
    ("address", "network"),
    [
        ("203.0.113.77", "203.0.113.0/24"),
        ("::ffff:198.51.100.9", "198.51.100.0/24"),
        ("2001:db8:1234:5678::1", "2001:db8:1234::/48"),
        ("testclient", "unknown"),
        (None, "unknown"),
    ],
)
def test_a_line_names_the_network_never_the_address(
    address: str | None, network: str
) -> None:
    assert describe_logged_network(address) == network


def test_a_line_carries_its_stable_fields(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="app.security")

    log_security_event(
        WEBHOOK_DELIVERY_REFUSED,
        path="/v1/channels/meta/webhook",
        reason="missing_signature",
        client_address="203.0.113.77",
        provider="meta",
    )

    assert security_lines(caplog) == [
        {
            "security_event": "webhook_delivery_refused",
            "path": "/v1/channels/meta/webhook",
            "reason": "missing_signature",
            "client_network": "203.0.113.0/24",
            "provider": "meta",
        }
    ]


def test_denials_and_rate_limits_of_routes_are_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger="app.security")
    client = build_client()

    forbidden = client.get("/v1/businesses/business_1/secret")
    unauthenticated = client.get("/v1/me", headers={"Authorization": SECRET_TOKEN})
    limited = [client.post("/v1/busy") for _ in range(3)]
    webhook = client.post(
        "/v1/channels/meta/webhook",
        content=b"{}",
        headers={"X-Hub-Signature-256": "sha256=" + "0" * 64},
    )

    assert forbidden.status_code == 403
    assert unauthenticated.status_code == 401
    assert [answer.status_code for answer in limited] == [429, 429, 429]
    assert webhook.status_code == 401
    lines = security_lines(caplog)
    assert [line["security_event"] for line in lines] == [
        AUTHORIZATION_DENIED,
        AUTHORIZATION_DENIED,
        # One line a minute per route and network, not one per refusal.
        RATE_LIMIT_TRIGGERED,
        WEBHOOK_DELIVERY_REFUSED,
    ]
    assert lines[0]["path"] == "GET /v1/businesses/{business_id}/secret"
    assert lines[0]["reason"] == "access_denied"
    assert lines[1]["reason"] == "authentication_required"
    assert lines[3]["provider"] == "meta"
    assert lines[3]["status"] == 401
    text = " ".join(record.getMessage() for record in caplog.records)
    assert "business_1" not in str(lines) + text
    assert "very-secret-token" not in str(lines) + text
    assert "203.0.113.77" not in str(lines) + text
