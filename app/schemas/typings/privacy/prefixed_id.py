"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class BusinessExportId(BasePrefixedTypedId):
    """Random identifier of one full export of a business's data (a ZIP)."""

    prefix = "business_export"


class SuppressionEntryId(BasePrefixedTypedId):
    """
    Identifier of one entry of a business's suppression list.

    Derived (UUID v5) from the business and the identity's digest, so the
    same customer saying STOP twice is one entry, and a check is one read
    by id.
    """

    prefix = "suppression_entry"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
