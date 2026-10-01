"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CallOffsetSeconds(BaseConstrainedTypedInt):
    """
    Seconds from the start of a call to one line of its transcript.

    Example:
        offset = CallOffsetSeconds(42)
    """

    ge = 0


class DeliveredMessageCount(BaseConstrainedTypedInt):
    """
    Platform messages sent for one reply (long replies are split).

    Example:
        delivered = DeliveredMessageCount(2)
    """

    ge = 0
    le = 1000


class WebhookMessageCount(BaseConstrainedTypedInt):
    """
    Number of customer messages in one webhook delivery, by outcome.

    Example:
        answered = WebhookMessageCount(3)
    """

    ge = 0


# Keep abc order for all non example types, if possible.
