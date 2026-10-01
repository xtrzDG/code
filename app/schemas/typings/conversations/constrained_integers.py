"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CallDurationSeconds(BaseConstrainedTypedInt):
    """Duration of a phone call in seconds."""

    ge = 0


class ContactMessageLimit(BaseConstrainedTypedInt):
    """Messages one contact may send per hour before the assistant pauses."""

    ge = 1
    le = 10000


class LlmTokenCount(BaseConstrainedTypedInt):
    """Number of language-model tokens."""

    ge = 0


class LlmTurnSequenceNumber(BaseConstrainedTypedInt):
    """Position of a raw turn inside a conversation transcript, from 0."""

    ge = 0


# Keep abc order for all non example types, if possible.
