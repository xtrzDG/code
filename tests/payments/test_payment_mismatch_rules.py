"""
Which differences between a provider's answer and a payment order move
money (`find_mismatch`): the provider took money the platform has unpaid,
failed or reversed a payment the platform has paid, or took money for a
renewal the order never recorded.
"""

import pytest

from app.schemas.constants.payments import PaymentStatus
from app.schemas.dto.payment_reconciliation import ProviderPaymentState
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.billing.reconciliation.payment_mismatch_rules import find_mismatch
from tests.payments.reconciliation_fakes import payment_order

APPROVED, DECLINED = PaymentStatus.APPROVED, PaymentStatus.DECLINED


def state(
    status: PaymentStatus, *, is_first: bool = True, is_recorded: bool = True
) -> ProviderPaymentState:
    return ProviderPaymentState(
        reference=PaymentProviderReference("ord_1"),
        status=status,
        is_first_payment=is_first,
        is_recorded_payment=is_recorded,
    )


@pytest.mark.parametrize(
    ("recorded", "is_settled", "provider", "is_first", "expected"),
    [
        (PaymentStatus.CREATED, False, APPROVED, True, "paid_at_provider"),
        (PaymentStatus.PROCESSING, False, APPROVED, True, "paid_at_provider"),
        (APPROVED, True, APPROVED, True, None),
        # A later charge declined; the first payment was paid at both.
        (DECLINED, True, APPROVED, True, None),
        (APPROVED, True, DECLINED, True, "failed_at_provider"),
        (APPROVED, True, PaymentStatus.EXPIRED, True, "failed_at_provider"),
        (APPROVED, True, PaymentStatus.REVERSED, True, "reversed_at_provider"),
        (PaymentStatus.REVERSED, True, PaymentStatus.REVERSED, True, None),
        (PaymentStatus.CREATED, False, PaymentStatus.PROCESSING, True, None),
        (PaymentStatus.CREATED, False, PaymentStatus.EXPIRED, True, None),
        # Stripe's latest invoice: paid there, declined here.
        (DECLINED, True, APPROVED, False, "paid_at_provider"),
        (APPROVED, True, DECLINED, False, "failed_at_provider"),
    ],
)
def test_only_differences_that_move_money_are_mismatches(
    recorded: PaymentStatus,
    is_settled: bool,
    provider: PaymentStatus,
    is_first: bool,
    expected: str | None,
) -> None:
    order = payment_order(BusinessId(), recorded, is_settled=is_settled)

    kind = find_mismatch(order, state(provider, is_first=is_first))

    assert (None if kind is None else kind.value) == expected


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        (APPROVED, "renewal_paid_at_provider"),
        (DECLINED, None),
        (PaymentStatus.REVERSED, None),
    ],
)
def test_a_renewal_the_order_never_recorded_differs_once_it_was_paid(
    provider: PaymentStatus, expected: str | None
) -> None:
    # The order's own (earlier) payment was paid at both.
    order = payment_order(BusinessId(), APPROVED, is_settled=True)

    kind = find_mismatch(order, state(provider, is_first=False, is_recorded=False))

    assert (None if kind is None else kind.value) == expected
