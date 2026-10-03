"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class DeliveryAttemptCount(BaseConstrainedTypedInt):
    """
    Send attempts of one outbox message so far.

    Example:
        attempts = DeliveryAttemptCount(2)
    """

    ge = 0
    le = 1000


class InboundProcessingAttemptCount(BaseConstrainedTypedInt):
    """
    Times processing of one inbox event started (a crashed turn runs again).

    Example:
        attempts = InboundProcessingAttemptCount(1)
    """

    ge = 0
    le = 1000


# Keep abc order for all non example types, if possible.
