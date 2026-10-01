"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class ChannelId(BasePrefixedTypedId):
    """Random identifier of a connected channel."""

    prefix = "channel"


# Keep abc order for all non example types, if possible.
