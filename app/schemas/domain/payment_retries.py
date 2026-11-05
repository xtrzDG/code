from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.payments import PaymentProvider, PaymentRetryOutcome
from app.schemas.typings.billing.constrained_integers import (
    MoneyAmountMinor,
    PaymentRetryAttempt,
)
from app.schemas.typings.billing.prefixed_id import (
    InvoiceId,
    PaymentRetryId,
    SubscriptionId,
)
from app.schemas.typings.billing.strings import (
    PaymentFailureReason,
    PaymentProviderReference,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class PaymentRetryAttemptDocument(BaseDocument):
    """
    One retry of a declined automatic charge (dunning): which invoice, which
    attempt (1 to 3, on days 1, 3 and 6 of the grace period), when it was
    due and made, and how it went. The id derives from the invoice and the
    attempt, so a retry is claimed once (inserted only if absent) whatever
    number of workers run the job; the provider's notification settles the
    invoice itself.
    """

    id: PaymentRetryId
    business_id: BusinessId
    subscription_id: SubscriptionId
    invoice_id: InvoiceId
    attempt: PaymentRetryAttempt
    provider: PaymentProvider
    outcome: PaymentRetryOutcome = PaymentRetryOutcome.CLAIMED
    amount_minor: MoneyAmountMinor
    currency_code: CurrencyCode
    due_at: Microseconds
    attempted_at: Microseconds
    payment_reference: PaymentProviderReference | None = None
    failure_reason: PaymentFailureReason | None = None
