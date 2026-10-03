"""A Flitt API stand-in for the billing tests that checks request signatures."""

import base64
import hashlib
import json
from dataclasses import dataclass, field

import httpx

from tests.billing.billing_settings import CHECKOUT_URL, FLITT_SECRET_KEY


@dataclass
class FlittSandbox:
    """Flitt API stand-in that verifies protocol 2.0 request signatures."""

    checkout_orders: list[dict[str, object]] = field(
        default_factory=list[dict[str, object]]
    )
    stopped_orders: list[str] = field(default_factory=list[str])
    refusal: dict[str, object] | None = None
    http_status: int = 200

    def handle(self, request: httpx.Request) -> httpx.Response:
        envelope: dict[str, object] = json.loads(request.content)["request"]
        data: str = str(envelope["data"])
        expected = hashlib.sha1(f"{FLITT_SECRET_KEY}|{data}".encode()).hexdigest()
        if envelope["signature"] != expected or envelope["version"] != "2.0":
            return httpx.Response(
                200,
                json={
                    "response": {
                        "response_status": "failure",
                        "error_message": "Invalid signature",
                        "error_code": 1014,
                    }
                },
            )

        order: dict[str, object] = json.loads(base64.b64decode(data))["order"]
        if self.http_status != 200:
            return httpx.Response(self.http_status, text="unavailable")

        if self.refusal is not None:
            return httpx.Response(200, json={"response": self.refusal})

        if request.url.path == "/api/subscription/":
            self.stopped_orders.append(str(order["order_id"]))
            return httpx.Response(
                200, json={"response": {"response_status": "success"}}
            )

        self.checkout_orders.append(order)
        return httpx.Response(
            200,
            json={
                "response": {
                    "response_status": "success",
                    "checkout_url": CHECKOUT_URL,
                    "payment_id": 802345671,
                }
            },
        )
