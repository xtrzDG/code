"""
The reconciliation's read-only questions to the providers over scripted
transports: Flitt's order status by our order id (a signed 2.0 answer),
Stripe's latest invoice or checkout session; an order a provider does not
know, or a provider that is not configured, says nothing.
"""

from app.adapters.payments.payment_status_reader_adapter import (
    PaymentStatusReaderAdapter,
)
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.billing.flitt_test_clients import build_client_with
from tests.payments.reconciliation_fakes import (
    flitt_status_transport,
    payment_order,
    stripe_transport,
)
from tests.payments.stripe_requests import build_stripe_client


def test_flitt_is_asked_for_the_status_of_our_order() -> None:
    order = payment_order(BusinessId(), PaymentStatus.CREATED)
    seen: list[str] = []
    reader = PaymentStatusReaderAdapter(
        build_client_with(flitt_status_transport({str(order.id): "approved"}, seen)),
        None,
    )

    found = reader.read_status(order)

    assert seen == [f"/api/status/order_id {order.id}"]
    assert found is not None
    assert found.status is PaymentStatus.APPROVED and found.is_first_payment


def test_an_order_flitt_does_not_know_says_nothing() -> None:
    order = payment_order(BusinessId(), PaymentStatus.CREATED)
    reader = PaymentStatusReaderAdapter(
        build_client_with(flitt_status_transport({}, [])), None
    )

    assert reader.read_status(order) is None
    assert PaymentStatusReaderAdapter(None, None).read_status(order) is None


def test_stripe_is_asked_for_the_latest_invoice_or_the_session() -> None:
    client = build_stripe_client(
        stripe_transport(
            {
                "in_paid": {"id": "in_paid", "status": "paid"},
                "in_void": {"id": "in_void", "status": "void"},
                "cs_open": {
                    "id": "cs_open",
                    "status": "open",
                    "payment_status": "unpaid",
                },
                "cs_gone": {
                    "id": "cs_gone",
                    "status": "expired",
                    "payment_status": "unpaid",
                },
                "cs_setup": {
                    "id": "cs_setup",
                    "status": "complete",
                    "payment_status": "no_payment_required",
                },
            }
        )
    )
    reader = PaymentStatusReaderAdapter(None, client)

    def status_of(reference: str) -> tuple[PaymentStatus, bool] | None:
        found = reader.read_status(
            payment_order(
                BusinessId(),
                PaymentStatus.APPROVED,
                provider=PaymentProvider.STRIPE,
                reference=reference,
            )
        )
        return None if found is None else (found.status, bool(found.is_first_payment))

    assert status_of("in_paid") == (PaymentStatus.APPROVED, False)
    assert status_of("in_void") == (PaymentStatus.DECLINED, False)
    assert status_of("cs_open") == (PaymentStatus.PROCESSING, True)
    assert status_of("cs_gone") == (PaymentStatus.EXPIRED, True)
    assert status_of("cs_setup") is None
    assert status_of("in_missing") is None
    assert status_of("pi_other") is None
