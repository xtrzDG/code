"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class BillingProfileId(BasePrefixedTypedId):
    """
    Identifier of a business's billing details.

    Derived (UUID v5) from the business: a business has one set of billing
    details, which every save finds instead of adding another.
    """

    prefix = "billing_profile"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
