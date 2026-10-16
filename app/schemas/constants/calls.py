from enum import StrEnum


class MissedCallReason(StrEnum):
    """
    Why a caller did not get through, or got nothing from the call.

    From the telephony line (PBX): NO_ANSWER (it rang out), BUSY, ABANDONED
    (the caller hung up before the assistant answered) and LINE_FAILED (the
    line could not put the call through). From the voice platform:
    NOT_STARTED (the assistant could not start the call), NO_SPEECH (the
    assistant answered, the caller hung up without a word) and
    TRANSFER_UNANSWERED (the caller asked for a person and nobody picked up).
    """

    NO_ANSWER = "no_answer"
    BUSY = "busy"
    ABANDONED = "abandoned"
    LINE_FAILED = "line_failed"
    NOT_STARTED = "not_started"
    NO_SPEECH = "no_speech"
    TRANSFER_UNANSWERED = "transfer_unanswered"


class MissedCallSource(StrEnum):
    """Who reported the missed call: the telephony line or the voice platform."""

    PBX = "pbx"
    VOICE_PLATFORM = "voice_platform"


class TextBackStatus(StrEnum):
    """
    Where the message to a caller who did not get through stands: QUEUED
    waits for the worker, SENT was accepted by WhatsApp or the SMS provider,
    FAILED could not be sent on any channel, SKIPPED was not sent on purpose
    (the reason is kept with it).
    """

    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class TextBackSkipReason(StrEnum):
    """
    Why a caller who did not get through was not texted.

    TURNED_OFF: the owner keeps text-backs off. OPTED_OUT: the customer
    asked for no more messages. ALREADY_TEXTED: the caller got one in the
    last day. DAILY_LIMIT: the business reached its daily number of
    text-backs. IN_CONVERSATION: the caller is already writing with the
    business. NO_CHANNEL: neither a WhatsApp template nor SMS can carry it.
    NOT_LIVE: the assistant is not live. NO_CALLER_NUMBER: the number was
    hidden. TOO_LATE: the call is too long ago to text about it now.
    """

    TURNED_OFF = "turned_off"
    OPTED_OUT = "opted_out"
    ALREADY_TEXTED = "already_texted"
    DAILY_LIMIT = "daily_limit"
    IN_CONVERSATION = "in_conversation"
    NO_CHANNEL = "no_channel"
    NOT_LIVE = "not_live"
    NO_CALLER_NUMBER = "no_caller_number"
    TOO_LATE = "too_late"


class TextBackChannel(StrEnum):
    """How the message to a caller who did not get through travels."""

    WHATSAPP = "whatsapp"
    SMS = "sms"


class CallTransferOutcome(StrEnum):
    """
    Whether a caller the phone assistant put through to staff got a
    person: NOT_TRANSFERRED (no transfer was tried), CONNECTED, UNANSWERED
    (nobody picked up, or the transfer failed).
    """

    NOT_TRANSFERRED = "not_transferred"
    CONNECTED = "connected"
    UNANSWERED = "unanswered"
