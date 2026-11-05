"""Names, versions and checksums of SQL migration files (pure functions)."""

import hashlib
from collections import Counter
from collections.abc import Iterable

from base_typed_string import BaseTypedStringConstraintViolationError

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.storage.constrained_strings import (
    SchemaMigrationChecksum,
    SchemaMigrationName,
)

MIGRATION_FILE_SUFFIX: str = ".sql"
MIGRATION_VERSION_LENGTH: int = 4
# The header of a file that runs outside a transaction (CREATE INDEX
# CONCURRENTLY): one of the comment lines before its first statement.
NO_TRANSACTION_HEADER: str = "-- workshop:no-transaction"


def migration_name_from_file_name(file_name: str) -> SchemaMigrationName:
    """
    "0001_document_collections.sql" -> SchemaMigrationName("0001_document_collections").

    Raises ValidationFailedError for anything else, so a typo in a file name
    stops the run instead of silently skipping a migration.
    """

    if not file_name.endswith(MIGRATION_FILE_SUFFIX):
        raise ValidationFailedError(
            f"Migration file {file_name!r} must end with {MIGRATION_FILE_SUFFIX!r}."
        )

    raw_name: str = file_name.removesuffix(MIGRATION_FILE_SUFFIX)
    try:
        return SchemaMigrationName(raw_name)
    except BaseTypedStringConstraintViolationError as error:
        raise ValidationFailedError(
            f"Migration file {file_name!r} must be named like "
            "'0001_snake_case_slug.sql' (4-digit version, lowercase slug)."
        ) from error


def migration_version(migration_name: SchemaMigrationName) -> str:
    """The 4-digit version prefix that orders migrations."""

    return migration_name[:MIGRATION_VERSION_LENGTH]


def normalize_migration_sql(sql_text: str) -> str:
    """Use "\\n" line endings, so a checkout with CRLF keeps the same checksum."""

    return sql_text.replace("\r\n", "\n").replace("\r", "\n")


def has_no_transaction_header(sql_text: str) -> bool:
    """True when a comment line before the first statement is the header."""

    for line in normalize_migration_sql(sql_text).split("\n"):
        stripped: str = line.strip()
        if stripped == NO_TRANSACTION_HEADER:
            return True

        if stripped != "" and not stripped.startswith("--"):
            return False

    return False


def compute_migration_checksum(sql_text: str) -> SchemaMigrationChecksum:
    """SHA-256 of the normalized SQL text, as lowercase hex."""

    normalized_sql: str = normalize_migration_sql(sql_text)
    return SchemaMigrationChecksum(
        hashlib.sha256(normalized_sql.encode("utf-8")).hexdigest()
    )


def find_duplicate_versions(
    migration_names: Iterable[SchemaMigrationName],
) -> list[str]:
    """Versions used by more than one migration, in ascending order."""

    version_counts: Counter[str] = Counter(
        migration_version(migration_name) for migration_name in migration_names
    )
    return sorted(version for version, count in version_counts.items() if count > 1)
