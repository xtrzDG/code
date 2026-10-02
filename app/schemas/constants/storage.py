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


class LookupFieldKind(StrEnum):
    """
    How a document field is indexed for lookups.

    TEXT and INTEGER fields are top-level fields stored by Postgres in a
    generated column `doc_<field>` (plain columns keep btree indexes usable
    under row-level security; expressions on the JSON document are not).
    TEXT fields are matched for equality, INTEGER fields by range and order.
    FILTER_TEXT fields have a column but no index of their own: they only
    narrow a query that an indexed field already selects (a message's
    direction within its conversation). ELEMENT_TEXT fields are a field of
    the objects of a top-level list (`members[].user_id`); a trigger keeps
    one row per value in `workshop.document_lookup_keys`.
    """

    TEXT = "text"
    FILTER_TEXT = "filter_text"
    INTEGER = "integer"
    ELEMENT_TEXT = "element_text"


class StorageScopeKind(StrEnum):
    """
    Whose rows a storage operation may see: one business, the platform (all
    businesses, an explicit escalation), or nobody's (UNSCOPED, the default
    of code that entered no scope: tenant collections are closed to it).
    """

    BUSINESS = "business"
    PLATFORM = "platform"
    UNSCOPED = "unscoped"


class StoredDocumentVersionState(StrEnum):
    """
    How a stored document's `schema_version` compares with this release's.

    OLDER documents are upcast on read and rewritten by `workshop
    migrate-documents`; NEWER ones were written by a newer release (during
    a rolling deploy or before a rollback) and are read tolerantly, never
    rewritten down.
    """

    OLDER = "older"
    CURRENT = "current"
    NEWER = "newer"
