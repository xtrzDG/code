"""A Stripe API stand-in for the billing tests: records what was asked."""

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from urllib.parse import parse_qsl

import httpx

from tests.billing.billing_settings import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET

STRIPE_CHECKOUT_URL: str = "https://checkout.stripe.com/c/pay/cs_test_0000"
STRIPE_PORTAL_URL: str = "https://billing.stripe.com/p/session/test_0000"
SAVED_CARD: dict[str, object] = {
    "id": "pm_test_0001",
    "card": {"brand": "visa", "last4": "4242", "exp_month": 9, "exp_year": 2030},
}


@dataclass
class StripeSandbox:
    """
    Stripe API stand-in that checks the secret key and the pinned version,
    answers like Stripe for the calls the adapter makes, and keeps them.
    """

    checkout_sessions: list[dict[str, str]] = field(
        default_factory=list[dict[str, str]]
    )
    portal_sessions: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    cancelled_subscriptions: list[str] = field(default_factory=list[str])
    paid_invoices: list[str] = field(default_factory=list[str])
    idempotency_keys: list[str] = field(default_factory=list[str])
    is_card_declined: bool = False
    payment_method: dict[str, object] = field(default_factory=lambda: SAVED_CARD)

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.headers.get("Authorization") != f"Bearer {STRIPE_SECRET_KEY}":
            return httpx.Response(401, json={"error": {"type": "invalid_request"}})

        if request.headers.get("Stripe-Version") != "2024-06-20":
            return httpx.Response(400, json={"error": {"type": "invalid_request"}})

        key: str | None = request.headers.get("Idempotency-Key")
        if key is not None:
            self.idempotency_keys.append(key)

        form: dict[str, str] = dict(parse_qsl(request.content.decode()))
        path: str = request.url.path
        if path == "/v1/checkout/sessions":
            self.checkout_sessions.append(form)
            return httpx.Response(
                200, json={"id": "cs_test_0000", "url": STRIPE_CHECKOUT_URL}
            )

        if path == "/v1/billing_portal/sessions":
            self.portal_sessions.append(form)
            return httpx.Response(
                200, json={"id": "bps_0000", "url": STRIPE_PORTAL_URL}
            )

        if path.startswith("/v1/subscriptions/") and request.method == "DELETE":
            self.cancelled_subscriptions.append(path.rsplit("/", 1)[-1])
            return httpx.Response(200, json={"status": "canceled"})

        if path.startswith("/v1/subscriptions/"):
            return httpx.Response(
                200,
                json={
                    "id": path.rsplit("/", 1)[-1],
                    "default_payment_method": self.payment_method,
                },
            )

        if path.startswith("/v1/payment_methods/"):
            return httpx.Response(200, json=self.payment_method)

        if path.startswith("/v1/invoices/") and path.endswith("/pay"):
            invoice_id: str = path.split("/")[3]
            self.paid_invoices.append(invoice_id)
            if self.is_card_declined:
                return httpx.Response(
                    402,
                    json={
                        "error": {
                            "type": "card_error",
                            "code": "card_declined",
                            "decline_code": "insufficient_funds",
                        }
                    },
                )

            return httpx.Response(200, json={"id": invoice_id, "status": "paid"})

        return httpx.Response(404, json={"error": {"type": "invalid_request"}})


def sign_stripe_event(payload: str, timestamp: int) -> str:
    """A `Stripe-Signature` header of the payload, as Stripe signs it."""

    signature: str = hmac.new(
        STRIPE_WEBHOOK_SECRET.encode(),
        f"{timestamp}.{payload}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def stripe_event(
    event_type: str,
    event_id: str,
    stripe_object: dict[str, object],
    created: int,
    previous: dict[str, object] | None = None,
) -> str:
    data: dict[str, object] = {"object": stripe_object}
    if previous is not None:
        data["previous_attributes"] = previous

    return json.dumps(
        {"id": event_id, "type": event_type, "created": created, "data": data}
    )
