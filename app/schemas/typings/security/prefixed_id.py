"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class KeyRotationId(BasePrefixedTypedId):
    """Random identifier of one re-encryption run of the stored secrets."""

    prefix = "key_rotation"


# Keep abc order for all non example types, if possible.
