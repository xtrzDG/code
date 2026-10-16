from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.typings.billing.booleans import IsInitialPaymentSettled, IsRefundDue
from app.schemas.typings.billing.constrained_integers import (
    BillingIntervalMonths,
    MoneyAmountMinor,
)
from app.schemas.typings.billing.constrained_strings import PaymentCheckoutUrl
from app.schemas.typings.billing.prefixed_id import (
    InvoiceId,
    PaymentOrderId,
    SubscriptionId,
)
from app.schemas.typings.billing.strings import (
    PaymentFailureReason,
    PaymentNotificationKey,
    PaymentProviderReference,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class PaymentOrderDocument(BaseDocument):
    """
    One checkout at the payment provider: the first charge for the listed
    invoices plus the automatic charges that follow it.

    The document id is sent as the provider order id. `recurring_amount_minor`
    is what every later automatic charge is expected to be. Processed
    notification keys make repeated provider notifications harmless.
    `is_refund_due` marks money the provider took that pays for nothing:
    a second payment of bills already paid, or an automatic charge of a
    schedule the subscription no longer uses; the platform admin refunds
    it.
    """

    id: PaymentOrderId = Field(default_factory=PaymentOrderId)
    business_id: BusinessId
    subscription_id: SubscriptionId
    provider: PaymentProvider
    invoice_ids: list[InvoiceId]
    amount_minor: MoneyAmountMinor
    currency_code: CurrencyCode
    recurring_amount_minor: MoneyAmountMinor
    recurring_interval_months: BillingIntervalMonths
    status: PaymentStatus = PaymentStatus.CREATED
    checkout_url: PaymentCheckoutUrl | None = None
    is_initial_payment_settled: IsInitialPaymentSettled = False
    is_refund_due: IsRefundDue = False
    last_payment_reference: PaymentProviderReference | None = None
    last_failure_reason: PaymentFailureReason | None = None
    processed_notification_keys: list[PaymentNotificationKey] = Field(
        default_factory=list[PaymentNotificationKey]
    )
