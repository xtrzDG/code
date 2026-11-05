"""A Flitt API stand-in for the billing tests that checks request signatures."""

import base64
import hashlib
import json
import time
from dataclasses import dataclass, field

import httpx

from tests.billing.billing_settings import CHECKOUT_URL, FLITT_SECRET_KEY

# Flitt's answer for an order it does not know.
UNKNOWN_ORDER: dict[str, object] = {
    "response_status": "failure",
    "error_message": "Order not found",
    "error_code": 1018,
}


@dataclass
class FlittSandbox:
    """Flitt API stand-in that verifies protocol 2.0 request signatures."""

    checkout_orders: list[dict[str, object]] = field(
        default_factory=list[dict[str, object]]
    )
    stopped_orders: list[str] = field(default_factory=list[str])
    recurring_orders: list[dict[str, object]] = field(
        default_factory=list[dict[str, object]]
    )
    recurring_status: str = "approved"
    refusal: dict[str, object] | None = None
    http_status: int = 200
    # What the status API answers per order id (`order_status`, `amount`,
    # `currency`): the callbacks a test delivers tell it (`know_callback`);
    # an order it was never told about is refused, as Flitt refuses one it
    # does not know.
    order_states: dict[str, dict[str, object]] = field(
        default_factory=dict[str, dict[str, object]]
    )
    status_queries: list[str] = field(default_factory=list[str])
    # How long the status API takes to answer (a slow provider).
    status_delay_seconds: float = 0.0

    def know_callback(self, parameters: dict[str, object]) -> None:
        """Flitt's own record of an order now matches this callback."""

        self.order_states[str(parameters.get("order_id"))] = {
            key: parameters[key]
            for key in ("order_status", "amount", "currency")
            if key in parameters
        }

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

        answer_fields: dict[str, object]
        if request.url.path == "/api/status/order_id":
            order_id: str = str(order["order_id"])
            self.status_queries.append(order_id)
            time.sleep(self.status_delay_seconds)
            known: dict[str, object] | None = self.order_states.get(order_id)
            if known is None:
                return httpx.Response(200, json={"response": UNKNOWN_ORDER})

            answer_fields = {"response_status": "success", "order_id": order_id}
            answer_fields.update(known)
        elif request.url.path == "/api/recurring/":
            self.recurring_orders.append(order)
            answer_fields = {
                "response_status": "success",
                "order_status": self.recurring_status,
                "payment_id": 802345900 + len(self.recurring_orders),
                "response_description": (
                    "" if self.recurring_status == "approved" else "Card declined"
                ),
            }
        else:
            self.checkout_orders.append(order)
            answer_fields = {"checkout_url": CHECKOUT_URL, "payment_id": 802345671}

        # As Flitt answers: a signed 2.0 envelope.
        answer: str = base64.b64encode(
            json.dumps({"order": answer_fields}).encode()
        ).decode()
        signature: str = hashlib.sha1(
            f"{FLITT_SECRET_KEY}|{answer}".encode()
        ).hexdigest()
        return httpx.Response(
            200,
            json={
                "response": {"version": "2.0", "data": answer, "signature": signature}
            },
        )
