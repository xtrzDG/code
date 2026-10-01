from enum import StrEnum


class ConversationStatus(StrEnum):
    """
    State of a customer conversation (concept: open, handoff, closed).

    While a conversation is in HANDOFF the assistant stays silent in chat
    channels until staff resolve the handoff.
    """

    OPEN = "open"
    HANDOFF = "handoff"
    CLOSED = "closed"


class MessageAuthor(StrEnum):
    """Who wrote a message."""

    CUSTOMER = "customer"
    ASSISTANT = "assistant"
    STAFF = "staff"
    SYSTEM = "system"


class LlmTurnRole(StrEnum):
    """Role of one raw turn in the language-model transcript."""

    USER = "user"
    ASSISTANT = "assistant"


class LlmStopReason(StrEnum):
    """Why the language model stopped generating."""

    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    REFUSAL = "refusal"
    PAUSE_TURN = "pause_turn"
    OTHER = "other"


class CallOutcome(StrEnum):
    """Result extracted from a finished phone call."""

    BOOKING = "booking"
    LEAD = "lead"
    HANDOFF = "handoff"
    UNANSWERED_QUESTION = "unanswered_question"
    INFORMATION = "information"
    ABANDONED = "abandoned"


class ReplyGuardVerdict(StrEnum):
    """Result of the invented-numbers guard on an assistant reply."""

    CLEAN = "clean"
    REWRITTEN = "rewritten"
    HANDED_OFF = "handed_off"
