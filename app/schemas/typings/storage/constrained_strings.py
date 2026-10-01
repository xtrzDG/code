"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


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
