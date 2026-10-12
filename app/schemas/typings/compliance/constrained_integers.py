"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AuditChainCount(BaseConstrainedTypedInt):
    """How many audit hash chains (businesses' and the platform's) are in a state."""

    ge = 0


class AuditChainEntryCount(BaseConstrainedTypedInt):
    """How many entries of one audit hash chain a check read or a purge removed."""

    ge = 0


class AuditChainPosition(BaseConstrainedTypedInt):
    """
    The place of an entry in its audit hash chain: 1 for the first entry
    the chain holds, one more for each entry after it.
    """

    ge = 1


class AuditPurgeBatchSize(BaseConstrainedTypedInt):
    """How many audit entries one purge statement removes at most."""

    ge = 1
    le = 10_000


class AuditRecordCount(BaseConstrainedTypedInt):
    """
    How many records one audited operation covered, when it covered many
    at once (a retention purge, a deletion at a sub-processor).
    """

    ge = 0


class AuditViewCount(BaseConstrainedTypedInt):
    """
    How many identical views one audited VIEW stands for: the first one and
    those of the same person, record and address within 5 minutes.
    """

    ge = 1


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
