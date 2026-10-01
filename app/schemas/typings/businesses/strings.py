"""Keep abc order."""

from base_typed_string import BaseTypedString


class AddressText(BaseTypedString):
    """Street address as the owner wrote it."""


class BusinessName(BaseTypedString):
    """Public name of a business."""


class CityName(BaseTypedString):
    """City of a business, in the owner's spelling."""


class RawManagerContactAddress(BaseTypedString):
    """
    Manager contact address as the owner typed it, before per-channel checks.

    Example:
        raw_address = RawManagerContactAddress("555 12 34 56")
    """


# Keep abc order for all non example types, if possible.
