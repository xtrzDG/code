from enum import StrEnum


class InboundEventKind(StrEnum):
    """What a webhook brought into the inbox, and so which job processes it."""

    CUSTOMER_MESSAGE = "customer_message"
    PLATFORM_BOT_UPDATE = "platform_bot_update"
    VOICE_POST_CALL = "voice_post_call"


class InboundEventStatus(StrEnum):
    """
    Where one inbox event stands.

    RECEIVED is stored and queued; PROCESSING is held by a worker (or the
    widget request) until `lease_until`, after which another may take it
    over; ANSWERED queued a reply (or finished the event); HANDED_OFF ended
    without an assistant reply because staff own the conversation; FAILED
    cannot be processed (the business is not live, the payload is invalid,
    or the retries ran out).
    """

    RECEIVED = "received"
    PROCESSING = "processing"
    ANSWERED = "answered"
    HANDED_OFF = "handed_off"
    FAILED = "failed"


class OutboundMessageKind(StrEnum):
    """Who an outbox message goes to."""

    CUSTOMER_REPLY = "customer_reply"
    STAFF_NOTIFICATION = "staff_notification"


class OutboundMessageStatus(StrEnum):
    """
    Delivery state of an outbox message: PENDING waits for its next attempt,
    DELIVERED reached the platform, DEAD was refused for good (a 4xx, no
    provider) or ran out of attempts.
    """

    PENDING = "pending"
    DELIVERED = "delivered"
    DEAD = "dead"


class DeliveryFailureKind(StrEnum):
    """
    Why one send attempt failed, which decides what happens next.

    RATE_LIMITED and TRANSIENT (5xx, timeouts, the network) are retried
    with backoff (after the platform's Retry-After when it named one);
    REJECTED (a 4xx: blocked bot, unknown recipient, closed 24-hour window),
    CREDENTIAL_REJECTED (the channel's token stopped working) and
    NOT_CONFIGURED (no provider for this kind of message) cannot succeed by
    trying again.
    """

    RATE_LIMITED = "rate_limited"
    TRANSIENT = "transient"
    REJECTED = "rejected"
    CREDENTIAL_REJECTED = "credential_rejected"
    NOT_CONFIGURED = "not_configured"
