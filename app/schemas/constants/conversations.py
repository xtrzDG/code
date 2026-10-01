from enum import StrEnum


class ConversationStatus(StrEnum):
    """State of a customer conversation."""

    OPEN = "open"
    HANDED_OFF = "handed_off"
    CLOSED = "closed"


class MessageAuthor(StrEnum):
    """Who wrote a customer-visible message."""

    CUSTOMER = "customer"
    ASSISTANT = "assistant"
    HUMAN_AGENT = "human_agent"


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
