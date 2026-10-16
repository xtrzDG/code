"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class LiveEventId(BaseConstrainedTypedString):
    """
    Identifier of one event of a business's live stream: when it was
    published (UNIX microseconds, 17 digits) and a random suffix. The
    cabinet sends the last one it saw as `Last-Event-ID` when it reconnects.

    Example:
        event_id = LiveEventId("01790812800000000-9f8e7d6c")
    """

    min_length = 26
    max_length = 26
    pattern = r"^[0-9]{17}-[0-9a-f]{8}$"


class LiveEventSubjectId(BaseConstrainedTypedString):
    """
    The id of what a live event is about (a booking, a handoff, a
    conversation, a channel, an autotest run), in its prefixed form.

    Example:
        subject_id = LiveEventSubjectId(
            "booking_53673d53-d10e-4b67-9997-748d56b12438"
        )
    """

    min_length = 3
    max_length = 80
    pattern = r"^[a-z][a-z_]*_[0-9a-f-]{8,64}$"
