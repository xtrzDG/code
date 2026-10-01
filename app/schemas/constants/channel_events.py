from enum import StrEnum


class PostCallEventStatus(StrEnum):
    """What happened to one post-call webhook of the voice platform."""

    RECORDED = "recorded"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"


class PlatformBotCommandResult(StrEnum):
    """How the platform Telegram bot handled one staff message."""

    LINKED = "linked"
    REJECTED_CODE = "rejected_code"
    CONTACT_LIMIT_REACHED = "contact_limit_reached"
    INSTRUCTIONS_SENT = "instructions_sent"
    IGNORED = "ignored"
