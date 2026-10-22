"""Provider-neutral payment DTOs: checkout sessions and verified notifications."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentProvider,
    PaymentStatus,
    PaymentWebhookOutcome,
)
from app.schemas.domain.billing_profiles import PaymentCardSnapshot
from app.schemas.domain.payment_methods import PaymentMethodSummary
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.booleans import IsPaymentRetry
from app.schemas.typings.billing.constrained_integers import BillingIntervalMonths
from app.schemas.typings.billing.constrained_strings import (
    AutoDebitStartDate,
    PaymentCheckoutUrl,
    PaymentReturnUrl,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentCardToken,
    PaymentFailureReason,
    PaymentProviderReference,
    PaymentWebhookBody,
    PaymentWebhookContentType,
    PaymentWebhookSignature,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag


class RecurringCharge(ImmutableDTO):
    """
    Automatic charge the provider repeats after the first payment, from
    `start_date` (the business-local day) or `starts_at` (the moment, for a
    provider that schedules by time).
    """

    amount: Money
    interval_months: BillingIntervalMonths
    start_date: AutoDebitStartDate
    starts_at: Microseconds


class PaymentCheckoutRequest(ImmutableDTO):
    """
    Ask `provider` for a hosted payment page: charge `amount` now, then
    `recurring_charge` automatically from its start date. A CARD_SETUP
    page charges nothing now and only saves the card for the automatic
    charges; with the `customer_reference` of a card already saved at
    Stripe, its billing portal replaces that card instead.
    """

    provider: PaymentProvider
    payment_order_id: PaymentOrderId
    amount: Money
    description: InvoiceDescription
    recurring_charge: RecurringCharge
    language: LanguageTag
    return_url: PaymentReturnUrl | None = None
    purpose: PaymentOrderPurpose = PaymentOrderPurpose.CHECKOUT
    customer_reference: PaymentProviderReference | None = None


class PaymentCheckoutSession(ImmutableDTO):
    """Hosted payment page the owner is sent to."""

    checkout_url: PaymentCheckoutUrl
    payment_reference: PaymentProviderReference | None = None


class PaymentWebhookDelivery(ImmutableDTO):
    """
    A provider notification exactly as it arrived, before verification:
    which provider's endpoint it reached, and its signature header (Stripe
    signs one; Flitt signs inside the body).
    """

    body: PaymentWebhookBody
    content_type: PaymentWebhookContentType | None = None
    provider: PaymentProvider = PaymentProvider.FLITT
    signature: PaymentWebhookSignature | None = None


class PaymentNotification(ImmutableDTO):
    """
    A provider notification whose signature and merchant were verified.

    `order_reference` is the order id we sent (an automatic charge may carry
    its own order id and point to ours through `parent_order_reference`);
    `merchant_reference` is the merchant data we sent, echoed back;
    `card` the masked card of an approved payment, when the provider says;
    `is_retry` marks a retry of a declined automatic charge (the dunning
    job tells the owners about those itself).
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
    is_retry: IsPaymentRetry = False


class PaymentMethodNotice(ImmutableDTO):
    """
    A card saved for the automatic charges of a payment order (`summary`,
    as the provider reported it): with the first payment of a checkout, or
    through the provider's own page later. `order_reference` names our
    payment order; `schedule_reference` and `customer_reference` are the
    provider's own (Stripe's subscription and customer); `card_token` is
    the token that charges the card again (Flitt's rectoken). `event_reference`
    makes a repeated notice harmless.
    """

    provider: PaymentProvider
    order_reference: PaymentProviderReference
    event_reference: PaymentProviderReference
    summary: PaymentMethodSummary | None = None
    schedule_reference: PaymentProviderReference | None = None
    customer_reference: PaymentProviderReference | None = None
    card_token: PaymentCardToken | None = None


class VerifiedPaymentEvent(ImmutableDTO):
    """
    What one verified provider notification says: a payment's status, a
    saved card, both (Flitt's approval of a first payment), or neither (an
    event the platform does not act on).
    """

    payment: PaymentNotification | None = None
    payment_method: PaymentMethodNotice | None = None


class PaymentWebhookReceipt(ImmutableDTO):
    """Answer to the provider: what the notification changed."""

    outcome: PaymentWebhookOutcome
    payment_order_id: PaymentOrderId | None = None
