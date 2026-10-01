"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class InvoiceId(BasePrefixedTypedId):
    """Random identifier of an invoice."""

    prefix = "invoice"


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
