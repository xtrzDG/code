"""
The integrations in the authorization matrix: the bodies of the webhook
and API key changes, the operations only owners may call (all of them),
and a webhook, its test delivery and an API key of business B.
"""

from typing import Any

from tests.e2e.harness import Workshop

type JsonObject = dict[str, Any]

B: str = "/v1/businesses/{business_id}"
WEBHOOK: str = f"{B}/webhooks/{{webhook_id}}"
DELIVERY: str = f"{B}/webhook-deliveries/{{delivery_id}}"
WEBHOOK_BODY: JsonObject = {
    "url": "https://hooks.example.com/matrix",
    "event_types": ["booking.created"],
}
INTEGRATION_BODIES: dict[str, JsonObject] = {
    f"POST {B}/webhooks": WEBHOOK_BODY,
    f"PATCH {WEBHOOK}": {"label": "Matrix"},
    f"POST {B}/api-keys": {"name": "Matrix", "scopes": ["leads:read"]},
}
OWNER_ONLY_INTEGRATION_OPERATIONS: frozenset[str] = frozenset(
    {
        f"GET {B}/webhooks",
        f"POST {B}/webhooks",
        f"PATCH {WEBHOOK}",
        f"DELETE {WEBHOOK}",
        f"POST {WEBHOOK}/rotate-secret",
        f"POST {WEBHOOK}/test",
        f"GET {WEBHOOK}/deliveries",
        f"GET {DELIVERY}",
        f"POST {DELIVERY}/retry",
        f"GET {B}/api-keys",
        f"POST {B}/api-keys",
        f"DELETE {B}/api-keys/{{api_key_id}}",
    }
)


def integration_path_values(
    workshop: Workshop, business_id: str, owner_headers: dict[str, str]
) -> dict[str, str]:
    """webhook_id, delivery_id (its test event) and api_key_id of business B."""

    base = f"/v1/businesses/{business_id}"
    webhook = workshop.client.post(
        f"{base}/webhooks", json=WEBHOOK_BODY, headers=owner_headers
    )
    assert webhook.status_code == 201, webhook.text
    webhook_id = str(webhook.json()["endpoint"]["id"])
    delivery = workshop.client.post(
        f"{base}/webhooks/{webhook_id}/test", headers=owner_headers
    )
    assert delivery.status_code == 200, delivery.text
    api_key = workshop.client.post(
        f"{base}/api-keys",
        json={"name": "Matrix", "scopes": ["leads:read"]},
        headers=owner_headers,
    )
    assert api_key.status_code == 201, api_key.text
    return {
        "webhook_id": webhook_id,
        "delivery_id": str(delivery.json()["id"]),
        "api_key_id": str(api_key.json()["api_key"]["id"]),
    }
