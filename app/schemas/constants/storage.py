from enum import StrEnum


class CollectionIsolation(StrEnum):
    """
    How a document collection is isolated between businesses in Postgres.

    TENANT collections follow the ambient storage scope: inside a business
    scope row-level security shows and accepts only that business's rows.
    PLATFORM collections (users, sessions, one-time codes, the audit log, the
    job queue, businesses themselves) are always read platform-wide.
    """

    TENANT = "tenant"
    PLATFORM = "platform"


class StorageScopeKind(StrEnum):
    """Whose rows a storage operation may see: one business or the platform."""

    BUSINESS = "business"
    PLATFORM = "platform"
