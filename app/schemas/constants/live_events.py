"""What the cabinet's live event stream reports."""

from enum import StrEnum


class LiveEventKind(StrEnum):
    """
    Something changed in a business, as the cabinet's live stream names it.
    The cabinet reloads what the change touches; the event carries ids
    only, never customer text.
    """

    AUTOTEST_PROGRESS = "autotest.progress"
    BILLING_CHANGED = "billing.changed"
    BOOKING_CHANGED = "booking.changed"
    BOOKING_CREATED = "booking.created"
    CHANNEL_CHANGED = "channel.changed"
    CHANNEL_ERROR = "channel.error"
    CONVERSATION_MESSAGE = "conversation.message"
    HANDOFF_CREATED = "handoff.created"
    HANDOFF_RESOLVED = "handoff.resolved"
    LEAD_CHANGED = "lead.changed"
    LEAD_CREATED = "lead.created"


class LiveStreamSignal(StrEnum):
    """
    Events of the stream itself rather than of the business: `stream.ready`
    opens every stream; `stream.resync` says events may have been missed
    (the reconnect came too late to replay them, or the server's listener
    reconnected), so the cabinet reloads everything it shows.
    """

    READY = "stream.ready"
    RESYNC = "stream.resync"
