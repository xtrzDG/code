"""
Settings → Integrations hand out lasting access: an API key outlives the
session that made it, and a webhook sends the business's events to an
outside address signed with a secret. Creating either, changing an
endpoint and rotating its secret need a recent sign-in or confirmation
(step-up): a stolen, older session cannot make itself a lasting door.
Reading the lists and revoking a key stay open.
"""

from typing import Any

from httpx2 import Response

from tests.integrations.integration_shop import (
    ALL_SCOPES,
    RECEIVER_URL,
    IntegrationShop,
    open_integration_shop,
)
from tests.users.mfa.mfa_api import STEP_UP_SECONDS, reason_codes


def assert_step_up_required(response: Response) -> None:
    assert response.status_code == 401, response.text
    assert reason_codes(response) == ["step_up_required"]
    assert response.json()["reasons"][0]["details"] == [str(STEP_UP_SECONDS)]


def confirm_with_login_code(shop: IntegrationShop) -> None:
    """Step-up with a login code sent to the owner's own phone."""

    started = shop.post("/v1/auth/step-up")
    assert started.status_code == 200, started.text
    confirmed = shop.post(
        "/v1/auth/step-up/verify",
        {
            "challenge_id": started.json()["login_code"]["challenge_id"],
            "login_code": str(shop.workshop.otp.codes[-1].code),
        },
    )
    assert confirmed.status_code == 200, confirmed.text


def test_keys_and_webhooks_need_a_recent_confirmation() -> None:
    with open_integration_shop() as shop:
        created = shop.add_webhook()
        endpoint: str = f"{shop.base}/webhooks/{created['endpoint']['id']}"
        shop.workshop.clock.advance(STEP_UP_SECONDS + 1)
        calls: list[tuple[str, str, dict[str, Any] | None]] = [
            ("POST", f"{shop.base}/api-keys", {"name": "Zapier", "scopes": ALL_SCOPES}),
            (
                "POST",
                f"{shop.base}/webhooks",
                {"url": RECEIVER_URL, "event_types": ["booking.created"]},
            ),
            ("PATCH", endpoint, {"label": "New CRM"}),
            ("POST", f"{endpoint}/rotate-secret", None),
        ]
        refused = [
            shop.client.request(method, url, json=body, headers=shop.headers)
            for method, url, body in calls
        ]
        keys = shop.get(f"{shop.base}/api-keys")
        webhooks = shop.get(f"{shop.base}/webhooks")

    for response in refused:
        assert_step_up_required(response)
    assert keys.status_code == 200
    assert keys.json()["items"] == []
    assert webhooks.status_code == 200
    assert [item["label"] for item in webhooks.json()["items"]] == ["CRM"]


def test_a_confirmation_lets_the_owner_make_a_key_again() -> None:
    with open_integration_shop() as shop:
        shop.workshop.clock.advance(STEP_UP_SECONDS + 1)
        refused = shop.post(
            f"{shop.base}/api-keys", {"name": "Zapier", "scopes": ["leads:read"]}
        )
        confirm_with_login_code(shop)
        token = shop.add_api_key(scopes=["leads:read"])
        me = shop.api("GET", "/me", token)

    assert_step_up_required(refused)
    assert me.status_code == 200, me.text


def test_revoking_a_key_needs_no_confirmation() -> None:
    with open_integration_shop() as shop:
        shop.add_api_key()
        key_id = shop.get(f"{shop.base}/api-keys").json()["items"][0]["id"]
        shop.workshop.clock.advance(STEP_UP_SECONDS + 1)
        revoked = shop.delete(f"{shop.base}/api-keys/{key_id}")

    # Closing a door is never slowed down.
    assert revoked.status_code == 204
