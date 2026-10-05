"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class DocumentBucketIndex(BaseConstrainedTypedInt):
    """
    Which bucket of an aggregation an integer field fell into: the position
    of the largest bucket start not after the value (0 for the first).
    """

    ge = 0


class DocumentCount(BaseConstrainedTypedInt):
    """How many stored documents a query counted or deleted."""

    ge = 0


class DocumentQueryLimit(BaseConstrainedTypedInt):
    """At most this many documents one query returns."""

    ge = 1
    le = 10_000


class DocumentSchemaVersionNumber(BaseConstrainedTypedInt):
    """
    Version of a stored document's shape within its collection: the number
    in its `schema_version` ("1", "2", ...). Upcasters upgrade stored JSON
    from one version to the next (`app/adapters/storage/document_upgrades.py`).
    """

    ge = 1


class DocumentUpgradeBatchSize(BaseConstrainedTypedInt):
    """How many stored documents one transaction of `migrate-documents` reads."""

    ge = 1
    le = 10_000


class LockWaitSeconds(BaseConstrainedTypedInt):
    """
    How long a caller waits for a lock that someone else holds before it
    gives up (the request fails instead of hanging).
    """

    ge = 1
    le = 600


class LookupBackfillBatchCount(BaseConstrainedTypedInt):
    """How many keyset batches `workshop backfill-lookup` ran for a column."""

    ge = 0


class LookupBackfillBatchSize(BaseConstrainedTypedInt):
    """
    How many rows one transaction of `workshop backfill-lookup` looks at
    (in primary-key order): small enough that its row locks are held for
    milliseconds, large enough that a big table takes few round trips.
    """

    ge = 1
    le = 50_000


class MigrationAttemptLimit(BaseConstrainedTypedInt):
    """
    How many times the migration runner tries one file whose locks were not
    granted in time (`lock_timeout`) before the deploy fails.
    """

    ge = 1
    le = 20


class MigrationAttemptNumber(BaseConstrainedTypedInt):
    """Which try of one migration file this is (the first is 1)."""

    ge = 1
    le = 20


# Keep abc order for all non example types, if possible.
