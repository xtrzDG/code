"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class BusinessId(BasePrefixedTypedId):
    """Random identifier of a business (tenant)."""

    prefix = "business"


# Keep abc order for all non example types, if possible.
