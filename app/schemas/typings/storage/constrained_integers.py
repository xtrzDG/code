"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


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


# Keep abc order for all non example types, if possible.
