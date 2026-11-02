from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.payment_reconciliation import PaymentMismatchKind
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.typings.billing.constrained_integers import ReconciledOrderCount
from app.schemas.typings.billing.constrained_strings import ReconciliationDay
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class PaymentMismatch(PersistentDocument):
    """
    One payment order whose status at its provider differs from the
    platform's record: what each side says and how they differ. No card
    data, no amounts, no person.
    """

    payment_order_id: PaymentOrderId
    business_id: BusinessId
    provider: PaymentProvider
    recorded_status: PaymentStatus
    provider_status: PaymentStatus
    kind: PaymentMismatchKind


class PaymentReconciliationDocument(BaseDocument):
    """
    The result of one daily payment reconciliation (a platform collection
    stored under its UTC day, migration 1230): how many recent payment
    orders were compared with Flitt or Stripe (`checked_count`), how many
    the provider could not tell about (`unreadable_count`) and the
    mismatches found. The `payment_mismatch` alert and the admin's
    reconciliation view read the latest one; a run again the same day
    (the admin's "Reconcile now") replaces it.
    """

    day: ReconciliationDay
    ran_at: Microseconds
    checked_count: ReconciledOrderCount
    unreadable_count: ReconciledOrderCount
    mismatches: list[PaymentMismatch] = Field(default_factory=list[PaymentMismatch])
