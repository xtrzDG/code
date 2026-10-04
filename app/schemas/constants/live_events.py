"""What the cabinet's live event stream reports."""

from enum import StrEnum


class LiveEventKind(StrEnum):
    """
    Something changed in a business, as the cabinet's live stream names it.
    The cabinet reloads what the change touches; the event carries ids
    only, never customer text.
    """

    ASSISTANT_APPLY = "assistant.apply"
    AUTOTEST_PROGRESS = "autotest.progress"
    BOOKING_CHANGED = "booking.changed"
    BOOKING_CREATED = "booking.created"
    CHANNEL_CHANGED = "channel.changed"
    CHANNEL_ERROR = "channel.error"
    CONVERSATION_ASSIGNED = "conversation.assigned"
    CONVERSATION_MESSAGE = "conversation.message"
    CONVERSATION_NOTE = "conversation.note"
    HANDOFF_CREATED = "handoff.created"
    HANDOFF_RESOLVED = "handoff.resolved"
    # A resolved handoff waits for a person again (staff undid "Resolved").
    HANDOFF_REOPENED = "handoff.reopened"
    KNOWLEDGE_IMPORT_PROGRESS = "knowledge_import.progress"
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
