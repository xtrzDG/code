"""Keep abc order."""

from base_typed_string import BaseTypedString


class AddressText(BaseTypedString):
    """Street address as the owner wrote it."""


class BusinessName(BaseTypedString):
    """Public name of a business."""


class CityName(BaseTypedString):
    """City of a business, in the owner's spelling."""


# Keep abc order for all non example types, if possible.
