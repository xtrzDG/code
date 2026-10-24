"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class MetaConnectionStateId(BasePrefixedTypedId):
    """Random identifier of one Facebook sign-in started in the cabinet."""

    prefix = "meta_connection_state"


# Keep abc order for all non example types, if possible.
