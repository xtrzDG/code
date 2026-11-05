"""Retrying a declined automatic charge (dunning) and telling the owners."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.payments import (
    DunningNoticeKind,
    PaymentProvider,
    PaymentStatus,
)
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import PaymentRetryAttempt
from app.schemas.typings.billing.prefixed_id import (
    InvoiceId,
    PaymentOrderId,
    PaymentRetryId,
)
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentCardToken,
    PaymentFailureReason,
    PaymentProviderReference,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag


class PaymentRetryRequest(ImmutableDTO):
    """
    Charge the saved card again for an unpaid invoice. `retry_id` makes the
    request idempotent at the provider (a request sent twice charges once);
    Stripe pays its own invoice again (`failed_charge_reference`), Flitt
    charges the saved card's token (`card_token`) for `amount`, its
    notification naming `payment_order_id`.
    """

    provider: PaymentProvider
    retry_id: PaymentRetryId
    payment_order_id: PaymentOrderId
    attempt: PaymentRetryAttempt
    amount: Money
    description: InvoiceDescription
    language: LanguageTag
    failed_charge_reference: PaymentProviderReference | None = None
    card_token: PaymentCardToken | None = None


class PaymentRetryResult(ImmutableDTO):
    """
    The provider's immediate answer to a retry: APPROVED, DECLINED, or
    PROCESSING (the answer comes by notification). Its notification
    settles the invoice either way.
    """

    status: PaymentStatus
    payment_reference: PaymentProviderReference | None = None
    failure_reason: PaymentFailureReason | None = None


class DunningNotice(ImmutableDTO):
    """
    What the owners are told after a retry: it was declined (and when the
    next one is, or that it was the last before the assistant only takes
    requests on `grace_until`), or the payment went through.
    """

    business_id: BusinessId
    kind: DunningNoticeKind
    invoice_id: InvoiceId
    attempt: PaymentRetryAttempt
    amount: Money
    grace_until: Microseconds | None = None
    next_retry_at: Microseconds | None = None
