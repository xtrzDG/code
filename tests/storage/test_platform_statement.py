"""
A self-scoped platform statement runs on its own (autocommit) and its
database failures become application errors like a platform transaction's;
a programming error stays what it is.
"""

import psycopg
import pytest

from app.adapters.storage.postgres.platform_transaction import (
    platform_statement,
    read_document_text,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.strings import DatabaseUrl


def test_a_statement_commits_on_its_own(database_url: DatabaseUrl) -> None:
    pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        with platform_statement(pool, "rate_limit_buckets") as connection:
            in_transaction = connection.execute(
                "select now() = statement_timestamp()"
            ).fetchone()
            status = connection.info.transaction_status
    finally:
        pool.close()

    # No transaction block was opened around it: it was its own transaction.
    assert in_transaction == (True,)
    assert status is psycopg.pq.TransactionStatus.IDLE


def test_a_missing_table_is_an_application_error(database_url: DatabaseUrl) -> None:
    pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        with (
            pytest.raises(ExternalServiceError, match="no table yet"),
            platform_statement(pool, "nowhere") as connection,
        ):
            connection.execute("select * from workshop.nowhere")
    finally:
        pool.close()


def test_a_programming_error_is_raised_as_it_is(database_url: DatabaseUrl) -> None:
    pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        with (
            pytest.raises(psycopg.errors.SyntaxError),
            platform_statement(pool, "rate_limit_buckets") as connection,
        ):
            connection.execute("selec 1")
    finally:
        pool.close()


def test_a_document_that_is_not_text_is_a_storage_error() -> None:
    assert read_document_text(('{"a": 1}',), "jobs") == '{"a": 1}'
    with pytest.raises(ExternalServiceError):
        read_document_text((7,), "jobs")
