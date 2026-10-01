"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class InvoiceId(BasePrefixedTypedId):
    """Random identifier of an invoice."""

    prefix = "invoice"


class SubscriptionId(BasePrefixedTypedId):
    """Random identifier of a subscription."""

    prefix = "subscription"


class UsageEventId(BasePrefixedTypedId):
    """Random identifier of one metered usage event."""

    prefix = "usage_event"


# Keep abc order for all non example types, if possible.
