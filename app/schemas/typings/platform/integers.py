"""Keep abc order."""

from base_typed_int import BaseTypedInt


class ListSortValue(BaseTypedInt):
    """
    A value a keyset list is sorted by at the end of a page (a timestamp, a
    count): with the item's key, where the next page starts.
    """


# Keep abc order for all non example types, if possible.
