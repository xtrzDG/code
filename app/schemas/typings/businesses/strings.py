"""Keep abc order."""

from base_typed_string import BaseTypedString


class BusinessAddress(BaseTypedString):
    """Street address of a business as the owner wrote it."""


class BusinessName(BaseTypedString):
    """Public name of a business."""


# Keep abc order for all non example types, if possible.
