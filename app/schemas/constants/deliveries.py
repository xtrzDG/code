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
    """
    What an outbox message is: an assistant reply to a customer, a
    notification to staff, or one of the messages a customer gets besides
    the assistant's replies: a staff member's reply written in the cabinet
    (STAFF_REPLY), a reminder of a booking (BOOKING_REMINDER), the written
    confirmation of a booking made on the phone (CALL_CONFIRMATION), the
    links the phone assistant promised (CALL_LINKS) and the message to a
    caller who did not get through (TEXT_BACK), and a guest's written
    confirmation of a booking the assistant made or moved in a chat, with
    its manage link (BOOKING_CONFIRMATION).
    """

    CUSTOMER_REPLY = "customer_reply"
    STAFF_NOTIFICATION = "staff_notification"
    STAFF_REPLY = "staff_reply"
    BOOKING_REMINDER = "booking_reminder"
    CALL_CONFIRMATION = "call_confirmation"
    CALL_LINKS = "call_links"
    TEXT_BACK = "text_back"
    BOOKING_CONFIRMATION = "booking_confirmation"


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


class DeliveryFailureReason(StrEnum):
    """
    Why the last send attempt of an outbox message failed, in words a
    business owner can act on (the cabinet says it next to the message):
    the platform asked for a pause (RATE_LIMITED) or did not answer
    (PROVIDER_UNAVAILABLE), both tried again; it refused the message
    (RECIPIENT_REFUSED: a blocked bot, an unknown recipient, a closed
    24-hour window) or the WhatsApp template (TEMPLATE_REJECTED); the
    business's channel was disconnected (CHANNEL_DISCONNECTED) or its
    credential stopped working (CREDENTIAL_REJECTED); nothing can carry
    this kind of message (NOT_CONFIGURED); or its moment passed before it
    could go (EXPIRED: "you just called us" hours later).
    """

    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    RECIPIENT_REFUSED = "recipient_refused"
    TEMPLATE_REJECTED = "template_rejected"
    CHANNEL_DISCONNECTED = "channel_disconnected"
    CREDENTIAL_REJECTED = "credential_rejected"
    NOT_CONFIGURED = "not_configured"
    EXPIRED = "expired"


class OutboundDeliveryState(StrEnum):
    """
    Where a message to a customer stands, as the cabinet shows it: waiting
    for its first attempt (SENDING), tried and waiting for the next attempt
    after a temporary failure (RETRYING), DELIVERED, or given up (FAILED).
    """

    SENDING = "sending"
    RETRYING = "retrying"
    DELIVERED = "delivered"
    FAILED = "failed"
