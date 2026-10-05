"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class BillingCreditId(BasePrefixedTypedId):
    """
    Identifier of one line of a business's credit ledger: credit a platform
    admin granted, or credit an invoice used. A used line derives (UUID v5)
    from its invoice, so an invoice uses credit once.
    """

    prefix = "billing_credit"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


class InvoiceId(BasePrefixedTypedId):
    """Random identifier of an invoice."""

    prefix = "invoice"


class OnboardingRequestId(BasePrefixedTypedId):
    """
    Identifier of a business's request for a done-for-you setup.

    Derived (UUID v5) from the business: a business has one request, which
    a repeated choice of the option finds instead of opening another.
    """

    prefix = "onboarding_request"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class PackageUsageWarningId(BasePrefixedTypedId):
    """Random identifier of one package usage warning sent to an owner."""

    prefix = "package_usage_warning"


class PaymentOrderId(BasePrefixedTypedId):
    """
    Random identifier of one checkout attempt; sent to the payment provider as
    its order id, so every attempt is unique there.
    """

    prefix = "payment_order"


class SubscriptionId(BasePrefixedTypedId):
    """Random identifier of a subscription."""

    prefix = "subscription"


class UsageEventId(BasePrefixedTypedId):
    """Random identifier of one metered usage event."""

    prefix = "usage_event"


# Keep abc order for all non example types, if possible.
