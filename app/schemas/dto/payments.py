"""Provider-neutral payment DTOs: checkout sessions and verified notifications."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.payments import (
    PaymentProvider,
    PaymentStatus,
    PaymentWebhookOutcome,
)
from app.schemas.domain.billing_profiles import PaymentCardSnapshot
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import BillingIntervalMonths
from app.schemas.typings.billing.constrained_strings import (
    AutoDebitStartDate,
    PaymentCheckoutUrl,
    PaymentReturnUrl,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentFailureReason,
    PaymentProviderReference,
    PaymentWebhookBody,
    PaymentWebhookContentType,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag


class RecurringCharge(ImmutableDTO):
    """Automatic charge the provider repeats after the first payment."""

    amount: Money
    interval_months: BillingIntervalMonths
    start_date: AutoDebitStartDate


class PaymentCheckoutRequest(ImmutableDTO):
    """
    Ask the provider for a hosted payment page: charge `amount` now, then
    `recurring_charge` automatically from its start date.
    """

    payment_order_id: PaymentOrderId
    amount: Money
    description: InvoiceDescription
    recurring_charge: RecurringCharge
    language: LanguageTag
    return_url: PaymentReturnUrl | None = None


class PaymentCheckoutSession(ImmutableDTO):
    """Hosted payment page the owner is sent to."""

    checkout_url: PaymentCheckoutUrl
    payment_reference: PaymentProviderReference | None = None


class PaymentWebhookDelivery(ImmutableDTO):
    """A provider notification exactly as it arrived, before verification."""

    body: PaymentWebhookBody
    content_type: PaymentWebhookContentType | None = None


class PaymentNotification(ImmutableDTO):
    """
    A provider notification whose signature and merchant were verified.

    `order_reference` is the order id we sent (an automatic charge may carry
    its own order id and point to ours through `parent_order_reference`);
    `merchant_reference` is the merchant data we sent, echoed back;
    `card` the masked card of an approved payment, when the provider says.
    """

    provider: PaymentProvider
    order_reference: PaymentProviderReference
    parent_order_reference: PaymentProviderReference | None = None
    merchant_reference: PaymentProviderReference | None = None
    payment_reference: PaymentProviderReference | None = None
    status: PaymentStatus
    amount: Money | None = None
    failure_reason: PaymentFailureReason | None = None
    card: PaymentCardSnapshot | None = None


class PaymentWebhookReceipt(ImmutableDTO):
    """Answer to the provider: what the notification changed."""

    outcome: PaymentWebhookOutcome
    payment_order_id: PaymentOrderId | None = None
