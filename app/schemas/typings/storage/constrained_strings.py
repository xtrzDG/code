"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AdvisoryLockKey(BaseConstrainedTypedString):
    """
    What a database advisory lock serializes, as text: a purpose and the
    ids it covers ("bookings|biz_..."). Postgres locks its 64-bit hash
    (`hashtextextended`), so every process that names the same key waits
    for the same lock.

    Example:
        key = AdvisoryLockKey("login-code-sends")
    """

    min_length = 1
    max_length = 400


class DocumentCollectionName(BaseConstrainedTypedString):
    """
    Name of one document collection, which is also its Postgres table name.

    Lowercase snake case that starts with a letter and fits a Postgres
    identifier (at most 63 bytes), so it never needs quoting tricks.

    Example:
        collection_name = DocumentCollectionName("knowledge_items")
    """

    min_length = 2
    max_length = 63
    pattern = r"^[a-z][a-z0-9_]{1,62}\Z"


class DocumentFieldPath(BaseConstrainedTypedString):
    """
    A field of stored documents that queries may filter or sort by.

    A top-level field (`token_hash`), or a field of the objects in a
    top-level list (`members[].user_id`: matches when any member has it).
    Every path a collection is queried by is declared in
    `app/utilities/storage/document_lookup_fields.py` and indexed by the
    migrations; storage refuses undeclared paths. The pattern keeps it a
    safe part of a Postgres identifier (`doc_<path>`).

    Example:
        field = DocumentFieldPath("token_hash")
    """

    min_length = 1
    max_length = 100
    pattern = r"^[a-z][a-z0-9_]{0,47}(\[\]\.[a-z][a-z0-9_]{0,47})?\Z"


class SchemaMigrationChecksum(BaseConstrainedTypedString):
    """
    SHA-256 (lowercase hex) of a migration file with normalized line endings.

    Example:
        checksum = SchemaMigrationChecksum("9f86d081884c7d65...")
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}\Z"


class SchemaMigrationName(BaseConstrainedTypedString):
    """
    Migration file name without ".sql": a 4-digit version and a snake-case slug.

    Example:
        migration_name = SchemaMigrationName("0001_document_collections")
    """

    min_length = 6
    max_length = 120
    pattern = r"^[0-9]{4}_[a-z0-9][a-z0-9_]*\Z"


# Keep abc order for all non example types, if possible.
