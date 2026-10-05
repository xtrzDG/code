"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AuditRecordCount(BaseConstrainedTypedInt):
    """
    How many records one audited operation covered, when it covered many
    at once (a retention purge, a deletion at a sub-processor).
    """

    ge = 0


class DeletedRecordingCount(BaseConstrainedTypedInt):
    """Number of call recording files removed from recording storage."""

    ge = 0


class ErasedRecordCount(BaseConstrainedTypedInt):
    """
    Number of stored records of one kind erased or anonymized when a visitor's
    personal data is deleted.
    """

    ge = 0


class PurgedCallCount(BaseConstrainedTypedInt):
    """Number of calls that lost their recording and transcript by retention."""

    ge = 0


class ScannedBusinessCount(BaseConstrainedTypedInt):
    """Number of businesses checked by one retention purge run."""

    ge = 0


# Keep abc order for all non example types, if possible.
