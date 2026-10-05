from enum import StrEnum


class TurnGate(StrEnum):
    """
    What the conversation engine does with one customer message.

    ANSWER asks the language model. While staff own the conversation (open
    handoff) the assistant stays silent in chat and promises a call back on
    the phone. Past the per-contact message limit the assistant answers once
    with a polite stop message and then stays silent until the hour passes.
    A message with nothing the assistant can read (a sticker, a file, a voice
    note without words) gets the platform's request to write instead. A
    customer the owner blocked gets nothing at all (BLOCKED_SILENCE; a call
    ends), whatever they send; their messages still reach the inbox.
    """

    ANSWER = "answer"
    STAFF_SILENCE = "staff_silence"
    STAFF_CALLBACK = "staff_callback"
    LIMIT_NOTICE = "limit_notice"
    LIMIT_SILENCE = "limit_silence"
    ATTACHMENT_NOTICE = "attachment_notice"
    BLOCKED_SILENCE = "blocked_silence"


class ReplyFailureKind(StrEnum):
    """
    Why the language model could not produce a reply that may be sent: it
    refused, the provider failed, it did not finish, or its rewritten reply
    still had values (UNVERIFIED_NUMBERS) or policy and availability claims
    (UNSUPPORTED_CLAIM) the evidence does not back, or another person's
    phone or e-mail (PERSONAL_DATA).
    """

    REFUSAL = "refusal"
    PROVIDER_ERROR = "provider_error"
    NO_ANSWER = "no_answer"
    UNVERIFIED_NUMBERS = "unverified_numbers"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    PERSONAL_DATA = "personal_data"
