"""Payment orders, scripted Flitt and Stripe answers and a fake status reader."""

import base64
import hashlib
import json

import httpx
from typed_time_provider import Microseconds

from app.contracts.platform_safety import PaymentStatusReaderAdapterContract
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentProvider,
    PaymentStatus,
)
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_reconciliation import ProviderPaymentState
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.billing.constrained_integers import (
    BillingIntervalMonths,
    MoneyAmountMinor,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId, SubscriptionId
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from tests.billing.billing_settings import FLITT_SECRET_KEY

NOW: Microseconds = Microseconds(1_793_620_800_000_000)  # 2026-11-02 12:00 UTC
DAY: int = 24 * 60 * 60 * 1_000_000


def payment_order(
    business_id: BusinessId,
    status: PaymentStatus,
    *,
    provider: PaymentProvider = PaymentProvider.FLITT,
    is_settled: bool = False,
    written_days_ago: int = 1,
    purpose: PaymentOrderPurpose = PaymentOrderPurpose.CHECKOUT,
    reference: str | None = None,
    schedule: str | None = None,
) -> PaymentOrderDocument:
    written = Microseconds(int(NOW) - written_days_ago * DAY)
    return PaymentOrderDocument(
        business_id=business_id,
        subscription_id=SubscriptionId(),
        provider=provider,
        invoice_ids=[],
        amount_minor=MoneyAmountMinor(4_900),
        currency_code=CurrencyCode("EUR"),
        recurring_amount_minor=MoneyAmountMinor(4_900),
        recurring_interval_months=BillingIntervalMonths(1),
        status=status,
        is_initial_payment_settled=is_settled,
        purpose=purpose,
        last_payment_reference=(
            None if reference is None else PaymentProviderReference(reference)
        ),
        schedule_reference=(
            None if schedule is None else PaymentProviderReference(schedule)
        ),
        created_at=written,
        updated_at=written,
    )


class FakeStatusReader(PaymentStatusReaderAdapterContract):
    """Answers by order id: a status (first payment), None, or an outage."""

    def __init__(
        self,
        statuses: dict[PaymentOrderId, PaymentStatus | None],
        unreachable: frozenset[PaymentOrderId] = frozenset(),
    ) -> None:
        self._statuses: dict[PaymentOrderId, PaymentStatus | None] = statuses
        self._unreachable: frozenset[PaymentOrderId] = unreachable
        self.asked: list[PaymentOrderId] = []

    def read_status(
        self, payment_order: PaymentOrderDocument
    ) -> ProviderPaymentState | None:
        self.asked.append(payment_order.id)
        if payment_order.id in self._unreachable:
            raise ExternalServiceError("Flitt request failed: ConnectTimeout.")

        status: PaymentStatus | None = self._statuses.get(payment_order.id)
        if status is None:
            return None

        return ProviderPaymentState(
            reference=PaymentProviderReference(str(payment_order.id)),
            status=status,
            is_first_payment=True,
        )


def flitt_status_transport(
    statuses: dict[str, str], seen: list[str]
) -> httpx.MockTransport:
    """Flitt's order status API: a signed 2.0 answer, a refusal when unknown."""

    def handle(request: httpx.Request) -> httpx.Response:
        envelope: dict[str, object] = json.loads(request.content)["request"]
        order: dict[str, object] = json.loads(base64.b64decode(str(envelope["data"])))[
            "order"
        ]
        seen.append(f"{request.url.path} {order['order_id']}")
        status: str | None = statuses.get(str(order["order_id"]))
        if status is None:
            return httpx.Response(
                200,
                json={
                    "response": {
                        "response_status": "failure",
                        "error_message": "Order not found",
                        "error_code": 1018,
                    }
                },
            )

        answer: str = base64.b64encode(
            json.dumps(
                {"order": {"order_id": order["order_id"], "order_status": status}}
            ).encode()
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

    return httpx.MockTransport(handle)


def stripe_transport(
    objects: dict[str, dict[str, object]], seen: list[str] | None = None
) -> httpx.MockTransport:
    """Stripe's invoices, checkout sessions and subscriptions by id; 404 for others."""

    def handle(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(f"{request.url.path}?{request.url.query.decode()}")
        found: dict[str, object] | None = objects.get(
            request.url.path.rsplit("/", 1)[-1]
        )
        if found is None:
            return httpx.Response(
                404,
                json={
                    "error": {
                        "type": "invalid_request_error",
                        "code": "resource_missing",
                    }
                },
            )

        return httpx.Response(200, json=found)

    return httpx.MockTransport(handle)
