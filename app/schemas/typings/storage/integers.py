"""Keep abc order."""

from base_typed_int import BaseTypedInt


class DocumentFieldInteger(BaseTypedInt):
    """
    A stored document field's integer value (UNIX microseconds, sequence
    numbers): a bound of an indexed range query.
    """


# Keep abc order for all non example types, if possible.
