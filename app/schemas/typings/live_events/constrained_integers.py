"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class LiveStreamsPerUser(BaseConstrainedTypedInt):
    """
    How many live streams one person may keep open on one API process at
    once (tabs and devices).

    Example:
        limit = LiveStreamsPerUser(5)
    """

    ge = 1
    le = 100


# Keep abc order for all non example types, if possible.
