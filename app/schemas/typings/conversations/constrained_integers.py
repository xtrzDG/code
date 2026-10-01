"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class LlmTurnSequenceNumber(BaseConstrainedTypedInt):
    """Position of a raw turn inside a conversation transcript, from 0."""

    ge = 0


# Keep abc order for all non example types, if possible.
