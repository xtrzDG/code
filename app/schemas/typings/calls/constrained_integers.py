"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CallCollectedPartySize(BaseConstrainedTypedInt):
    """
    How many people a booking a caller asked for is for, as the voice
    platform's evaluation of the call read it from the conversation.
    """

    ge = 1
    le = 10000


# Keep abc order for all non example types, if possible.
