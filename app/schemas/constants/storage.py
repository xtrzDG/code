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
    ELEMENT_TEXT fields are a field of the objects of a top-level list
    (`members[].user_id`); a trigger keeps one row per value in
    `workshop.document_lookup_keys`.
    """

    TEXT = "text"
    INTEGER = "integer"
    ELEMENT_TEXT = "element_text"


class StorageScopeKind(StrEnum):
    """Whose rows a storage operation may see: one business or the platform."""

    BUSINESS = "business"
    PLATFORM = "platform"
