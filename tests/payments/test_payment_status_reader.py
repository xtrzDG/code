"""
The reconciliation's read-only questions to the providers over scripted
transports: Flitt's order status by our order id (a signed 2.0 answer),
Stripe's latest invoice or checkout session, and a Stripe subscription's
latest invoice (a renewal the order never recorded). A provider that is
not configured says nothing; a provider that refuses the read raises, so
the order counts as unreadable.
"""

import pytest

from app.adapters.payments.payment_status_reader_adapter import (
    PaymentStatusReaderAdapter,
)
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.exceptions.payment_errors import PaymentProviderRefusedError
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


def test_a_refused_read_is_unreadable_and_no_provider_says_nothing() -> None:
    order = payment_order(BusinessId(), PaymentStatus.CREATED)
    reader = PaymentStatusReaderAdapter(
        build_client_with(flitt_status_transport({}, [])), None
    )

    # Every order was opened at Flitt: a refusal is another merchant
    # account or revoked keys, never "nothing to compare".
    with pytest.raises(PaymentProviderRefusedError):
        reader.read_status(order)
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
    assert status_of("pi_other") is None
    with pytest.raises(PaymentProviderRefusedError):
        status_of("in_missing")


def subscription(invoice: dict[str, object]) -> dict[str, object]:
    return {"id": "sub_1", "latest_invoice": invoice}


@pytest.mark.parametrize(
    ("latest_invoice", "expected"),
    [
        # The order's own invoice, as it is.
        (
            {"id": "in_first", "status": "paid", "amount_paid": 4_900},
            (PaymentStatus.APPROVED, True),
        ),
        # A renewal the order never heard of.
        (
            {
                "id": "in_renewal",
                "status": "paid",
                "billing_reason": "subscription_cycle",
                "amount_paid": 4_900,
            },
            (PaymentStatus.APPROVED, False),
        ),
        # A renewal still being charged, and a trial's free first invoice.
        (
            {
                "id": "in_renewal",
                "status": "open",
                "billing_reason": "subscription_cycle",
                "amount_paid": 0,
            },
            None,
        ),
        (
            {
                "id": "in_trial",
                "status": "paid",
                "billing_reason": "subscription_create",
                "amount_paid": 0,
            },
            None,
        ),
        ({"id": "in_draft", "status": "draft"}, None),
    ],
)
def test_a_subscription_order_is_compared_with_its_latest_invoice(
    latest_invoice: dict[str, object], expected: tuple[PaymentStatus, bool] | None
) -> None:
    seen: list[str] = []
    reader = PaymentStatusReaderAdapter(
        None,
        build_stripe_client(
            stripe_transport({"sub_1": subscription(latest_invoice)}, seen)
        ),
    )

    found = reader.read_status(
        payment_order(
            BusinessId(),
            PaymentStatus.APPROVED,
            is_settled=True,
            provider=PaymentProvider.STRIPE,
            reference="in_first",
            schedule="sub_1",
        )
    )

    assert (
        None if found is None else (found.status, bool(found.is_recorded_payment))
    ) == expected
    if found is not None:
        assert not found.is_first_payment
    # One call: the subscription with its latest invoice expanded.
    (asked,) = seen
    assert asked.startswith("/v1/subscriptions/sub_1?") and "latest_invoice" in asked
