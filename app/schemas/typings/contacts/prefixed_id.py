"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class ContactId(BasePrefixedTypedId):
    """Random identifier of a customer contact of a business."""

    prefix = "contact"


# Keep abc order for all non example types, if possible.
