"""The daily reconciliation of payments with Flitt and Stripe."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.payment_reconciliation import PaymentMismatchKind
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.typings.billing.booleans import IsFirstPayment
from app.schemas.typings.billing.constrained_integers import ReconciledOrderCount
from app.schemas.typings.billing.constrained_strings import ReconciliationDay
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.users.prefixed_id import UserId


class ProviderPaymentState(ImmutableDTO):
    """
    What the payment provider says about a payment order: the status of
    the payment it was asked about (`reference`), and whether that is the
    order's first payment (Flitt's order, Stripe's checkout session) or
    its latest one (Stripe's latest invoice).
    """

    reference: PaymentProviderReference
    status: PaymentStatus
    is_first_payment: IsFirstPayment


class PaymentReconciliationQuery(ImmutableDTO):
    """A platform admin asks for the latest reconciliation."""

    user_id: UserId


class PaymentMismatchView(ImmutableDTO):
    """One mismatch as the admin sees it (the client's name, no card data)."""

    payment_order_id: PaymentOrderId
    business_id: BusinessId
    business_name: BusinessName | None = None
    provider: PaymentProvider
    recorded_status: PaymentStatus
    provider_status: PaymentStatus
    kind: PaymentMismatchKind


class PaymentReconciliationView(ImmutableDTO):
    """
    The latest reconciliation (today's, else yesterday's; None fields when
    none ran yet): when it ran, how many orders it compared and could not
    compare, and the mismatches.
    """

    day: ReconciliationDay | None = None
    ran_at: Microseconds | None = None
    checked_count: ReconciledOrderCount = ReconciledOrderCount(0)
    unreadable_count: ReconciledOrderCount = ReconciledOrderCount(0)
    mismatches: list[PaymentMismatchView] = Field(
        default_factory=list[PaymentMismatchView]
    )
