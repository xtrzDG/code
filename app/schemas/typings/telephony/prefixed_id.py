"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class PhoneNumberId(BasePrefixedTypedId):
    """
    Identifier of one number the platform rents for a business (W21), kept
    after the number goes back to the carrier as the record of the rental.

    Example:
        number_id = PhoneNumberId()
    """

    prefix = "phone_number"


class PhoneNumberRequestId(BasePrefixedTypedId):
    """
    Identifier of a business's request for a number the platform team
    arranges by hand. Derived (UUID v5) from the business, so a business has
    one request document, opened again when it asks again.
    """

    prefix = "phone_number_request"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
