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


class ConversationRating(StrEnum):
    """
    The owner's or staff's verdict on how the assistant handled a
    conversation (concept section 8, "good / bad" on the card), used in the
    weekly quality review (section 11).
    """

    GOOD = "good"
    BAD = "bad"


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


class StaffReplyBlock(StrEnum):
    """
    Why staff cannot write to a customer from the cabinet right now.

    VOICE_CALL: phone conversations have no written way back.
    TEST_CONVERSATION: owner test chats and autotests have no customer.
    WINDOW_CLOSED: WhatsApp, Instagram and Messenger accept free-form
    messages only within 24 hours of the customer's last message.
    UNSUPPORTED_CHANNEL: the channel has no outgoing messages here.
    CHANNEL_DISCONNECTED: the business's channel is no longer connected.
    """

    VOICE_CALL = "voice_call"
    TEST_CONVERSATION = "test_conversation"
    WINDOW_CLOSED = "window_closed"
    UNSUPPORTED_CHANNEL = "unsupported_channel"
    CHANNEL_DISCONNECTED = "channel_disconnected"


class StaffReplyRefusalCode(StrEnum):
    """Machine-readable reasons a staff reply is refused (409)."""

    # Meta refused the owner's WhatsApp template (name, language or its one
    # {{1}} variable): the owner corrects it in the channel settings.
    TEMPLATE_REJECTED = "template_rejected"


class StaffMessageDelivery(StrEnum):
    """
    How a staff message reaches the customer: sent through the messenger
    right away, sent in the owner's WhatsApp message template (after the
    24-hour window), or kept for the website chat, which shows it when the
    visitor's widget asks for new messages.
    """

    SENT = "sent"
    SENT_AS_TEMPLATE = "sent_as_template"
    STORED_FOR_WIDGET = "stored_for_widget"
