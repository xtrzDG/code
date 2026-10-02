"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class DocumentCount(BaseConstrainedTypedInt):
    """How many stored documents a query counted or deleted."""

    ge = 0


class DocumentQueryLimit(BaseConstrainedTypedInt):
    """At most this many documents one query returns."""

    ge = 1
    le = 10_000


# Keep abc order for all non example types, if possible.
