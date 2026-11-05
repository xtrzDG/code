"""
The window of one document-migration batch of the post-deploy data tasks:
the next `batch_size` rows of a table in `(created_at, row_sequence)`
order (the index every collection has), with the stored text only of the
rows whose `schema_version` (missing means "1") is not the current one.
Unlike `migrate-documents`, which selects only outdated rows and so may
scan a whole table in one statement, every batch looks at a bounded
number of rows.
"""

import re
from typing import Final

from psycopg import sql

from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.maintenance.constrained_strings import DataTaskPosition
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName

POSITION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(-?\d+):(-?\d+)\Z")


def compose_upgrade_window(collection_name: DocumentCollectionName) -> sql.Composed:
    """
    Parameters: after_created_at, after_row_sequence, current_version,
    batch_size. Rows: document_key, the document text when outdated (else
    NULL), created_at, row_sequence.
    """

    return sql.SQL(
        "select document_key, "
        "case when coalesce(document ->> 'schema_version', '1') "
        "<> %(current_version)s then document::text end, "
        "created_at, row_sequence "
        "from {table} "
        "where (created_at, row_sequence) > "
        "(%(after_created_at)s, %(after_row_sequence)s) "
        "order by created_at, row_sequence "
        "limit %(batch_size)s"
    ).format(table=sql.Identifier(DOCUMENT_SCHEMA_NAME, str(collection_name)))


def encode_window_position(created_at: int, row_sequence: int) -> DataTaskPosition:
    return DataTaskPosition(f"{created_at}:{row_sequence}")


def decode_window_position(position: DataTaskPosition) -> tuple[int, int]:
    """
    Raises:
        ExternalServiceError: the stored position is not one this adapter
            wrote (the task's state was edited by hand).
    """

    match = POSITION_PATTERN.match(str(position))
    if match is None:
        raise ExternalServiceError(
            f"The stored position {position!s} is not a creation time and row."
        )

    return int(match.group(1)), int(match.group(2))
