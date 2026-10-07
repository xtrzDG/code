"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class WebsiteImportId(BasePrefixedTypedId):
    """
    Random identifier of one import of a business's website: the job that
    reads it and the progress the cabinet follows carry it.
    """

    prefix = "website_import"


class WebsiteImportRecordId(BasePrefixedTypedId):
    """
    Identifier of the record of a business's current website import.

    Derived (UUID v5) from the business: a business has one current import,
    which every new import replaces.
    """

    prefix = "website_import_record"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
