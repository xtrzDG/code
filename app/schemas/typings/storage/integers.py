"""Keep abc order."""

from base_typed_int import BaseTypedInt


class DocumentFieldInteger(BaseTypedInt):
    """
    A stored document field's integer value (UNIX microseconds, sequence
    numbers): a bound of an indexed range query.
    """


class DocumentFieldSum(BaseTypedInt):
    """
    The sum of an integer field over the documents of one aggregation
    group (cost in micro-USD, seconds): a new quantity, not a field value.
    """


# Keep abc order for all non example types, if possible.
