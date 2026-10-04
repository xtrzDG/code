"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AnswersToImproveLimit(BaseConstrainedTypedInt):
    """How many answers to improve the Overview lists at most (`?limit=`)."""

    ge = 1
    le = 20


class CallDurationSeconds(BaseConstrainedTypedInt):
    """Duration of a phone call in seconds."""

    ge = 0


class ContactMessageLimit(BaseConstrainedTypedInt):
    """Messages one contact may send per hour before the assistant pauses."""

    ge = 1
    le = 10000


class ChatTurnDeadlineSeconds(BaseConstrainedTypedInt):
    """
    Seconds a customer of a messaging channel waits, from their first
    unanswered message, before the assistant sends a short "one moment"
    (CHAT_TURN_DEADLINE_SECONDS).
    """

    ge = 1
    le = 600


class ConversationMessageCount(BaseConstrainedTypedInt):
    """Number of stored messages in one conversation."""

    ge = 0


class InjectionFlagLimit(BaseConstrainedTypedInt):
    """
    Messages that look like prompt injection one contact may send in a day
    before the assistant stops answering them until the day passes
    (INJECTION_FLAG_LIMIT).
    """

    ge = 1
    le = 100


class LlmRoundCount(BaseConstrainedTypedInt):
    """Language-model calls one assistant reply took (tool rounds and rewrite)."""

    ge = 0


class LlmTokenCount(BaseConstrainedTypedInt):
    """Number of language-model tokens."""

    ge = 0


class LlmTurnSequenceNumber(BaseConstrainedTypedInt):
    """Position of a raw turn inside a conversation transcript, from 0."""

    ge = 0


class MessageCoalesceSeconds(BaseConstrainedTypedInt):
    """
    Quiet seconds the worker waits after a customer's latest message before
    answering, so quick messages in a row get one reply
    (MESSAGE_COALESCE_SECONDS; 0 answers at once).
    """

    ge = 0
    le = 60


class RecordingByteCount(BaseConstrainedTypedInt):
    """How many bytes of a call recording (its length, or a part's)."""

    ge = 0


class RecordingByteOffset(BaseConstrainedTypedInt):
    """Where a byte of a call recording lies, counted from 0."""

    ge = 0


class ReplyLatencyMilliseconds(BaseConstrainedTypedInt):
    """
    Milliseconds from the platform delivering a customer's (first
    unanswered) message to the assistant's reply being stored.
    """

    ge = 0


class StaffTemplateReplyMaxLength(BaseConstrainedTypedInt):
    """Most characters a staff reply sent as a WhatsApp template may have."""

    ge = 1


# Keep abc order for all non example types, if possible.
