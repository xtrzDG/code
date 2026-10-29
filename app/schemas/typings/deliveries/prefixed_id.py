"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class InboundEventId(BasePrefixedTypedId):
    """
    Identifier of one received webhook message in the inbox.

    Derived (UUID v5) from the business, the channel and the platform's own
    message id, so every redelivery of the same message names the same
    event and is stored once.
    """

    prefix = "inbound_event"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class OutboundMessageId(BasePrefixedTypedId):
    """
    Identifier of one message in the outbox.

    Derived (UUID v5) from the business and the message's idempotency key,
    so the same reply or notification is queued once however often the
    step that queues it runs again.
    """

    prefix = "outbound_message"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
