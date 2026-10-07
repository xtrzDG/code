"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class ContactId(BasePrefixedTypedId):
    """Random identifier of a customer contact of a business."""

    prefix = "contact"


class CustomerSegmentId(BasePrefixedTypedId):
    """Random identifier of a saved group of customers of a business."""

    prefix = "segment"


class CustomerSettingsId(BasePrefixedTypedId):
    """
    Identifier of how the team of one business works with its customers
    (whether staff see phone numbers, the tags in use).

    Derived (UUID v5) from the business: one settings document per business.
    """

    prefix = "customer_settings"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
