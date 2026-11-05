"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class MenuImportBatchId(BasePrefixedTypedId):
    """Random identifier of one menu import: the drafts it created share it."""

    prefix = "menu_import"


# Keep abc order for all non example types, if possible.
