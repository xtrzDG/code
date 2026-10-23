"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class BusinessClosureId(BasePrefixedTypedId):
    """
    The pending closure of one business (an owner closed it, or the unpaid
    subscription ended it): derived (UUID v5) from the business, so a
    business has at most one.
    """

    prefix = "business_closure"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


class BusinessDeletionId(BasePrefixedTypedId):
    """
    The deletion ledger's entry of one deleted business, which is also the
    number of its deletion certificate: derived (UUID v5) from the business,
    so a business is deleted (and certified) once.
    """

    prefix = "business_deletion"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


# Keep abc order for all non example types, if possible.
