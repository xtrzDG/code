from enum import StrEnum


class PostCallEventStatus(StrEnum):
    """
    What happened to one post-call webhook of the voice platform. The
    webhook only stores the report (QUEUED, or DUPLICATE when it came
    before); the worker then records the call (RECORDED).
    """

    RECORDED = "recorded"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"
    QUEUED = "queued"


class PlatformBotCommandResult(StrEnum):
    """
    How the platform Telegram bot handled one staff message. The webhook
    only stores the message (QUEUED); the worker then answers it.
    """

    LINKED = "linked"
    REJECTED_CODE = "rejected_code"
    CONTACT_LIMIT_REACHED = "contact_limit_reached"
    INSTRUCTIONS_SENT = "instructions_sent"
    IGNORED = "ignored"
    QUEUED = "queued"
