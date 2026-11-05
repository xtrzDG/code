"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class NoticeRecipientCount(BaseConstrainedTypedInt):
    """How many owners' addresses one notice was queued for."""

    ge = 0
    le = 1_000_000


class NotifiedBusinessCount(BaseConstrainedTypedInt):
    """How many businesses were told about one sub-processor change."""

    ge = 0
    le = 100_000_000


class SubprocessorNoticeDays(BaseConstrainedTypedInt):
    """
    How many days before a sub-processor change takes effect the owners
    are told about it (DPA section 8.3).
    """

    ge = 1
    le = 365


# Keep abc order for all non example types, if possible.
