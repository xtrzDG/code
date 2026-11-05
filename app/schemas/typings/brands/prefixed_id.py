"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class BrandId(BasePrefixedTypedId):
    """
    Random identifier of a brand: a chain of locations (businesses) run by
    one team under one name.
    """

    prefix = "brand"


# Keep abc order for all non example types, if possible.
