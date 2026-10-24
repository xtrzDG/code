"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class OutboundIdempotencyKey(BaseConstrainedTypedString):
    """
    What makes an outbox message unique within its business: the same key
    queues the message once.

    Example:
        key = OutboundIdempotencyKey("reply:conversation_1:message_2")
    """

    min_length = 1
    max_length = 300


class OutboundRecipientKey(BaseConstrainedTypedString):
    """
    One recipient of outbox messages (a customer in one channel, a staff
    contact): its messages are sent one at a time, in the order queued.

    Example:
        key = OutboundRecipientKey("customer:channel_1:9001")
    """

    min_length = 1
    max_length = 400


# Keep abc order for all non example types, if possible.
