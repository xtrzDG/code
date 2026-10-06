"""
Postgres as the platform's database: the server errors its documentation
lists (SQLSTATE codes with the server's own messages) arrive as the psycopg
classes the platform names, and each becomes what the platform promises -
the storage error the API answers with, a retry in migrations and
backfills, the end of a lock wait - so a renamed class or a moved code in a
psycopg or Postgres upgrade fails here.
"""

from typing import Any, cast

import psycopg
import pytest
from psycopg import errors as database_errors

from app.adapters.locks.postgres_advisory_lock_adapter import (
    SESSION_LOCK,
    acquire_lock,
)
from app.adapters.storage.postgres.migration_statements import RETRYABLE_ERRORS
from app.adapters.storage.postgres.postgres_session_settings import (
    translate_storage_error,
)
from app.clients.postgres.postgres_connection_pool_client import PostgresConnection
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey
from tests.contracts.contract_files import load_json_fixture

CASES: list[dict[str, Any]] = load_json_fixture("postgres", "server_errors.json")[
    "cases"
]


def server_error(case: dict[str, Any]) -> psycopg.Error:
    """The error psycopg raises for this SQLSTATE and server message."""

    error_class: type[psycopg.Error] = database_errors.lookup(case["code"])
    return error_class(f"{case['severity']}:  {case['message']}")


class LockConnection:
    """Sets lock_timeout, then fails the lock statement with the error."""

    def __init__(self, error: psycopg.Error) -> None:
        self.error: psycopg.Error = error
        self.statements: list[str] = []

    def execute(self, statement: str, parameters: object = None) -> None:
        self.statements.append(statement)
        if statement == SESSION_LOCK:
            raise self.error


def case_id(case: dict[str, Any]) -> str:
    return f"{case['code']}-{case['condition']}"


@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_documented_codes_arrive_as_the_classes_the_platform_names(
    case: dict[str, Any],
) -> None:
    error_class: type[psycopg.Error] = database_errors.lookup(case["code"])

    assert error_class.__name__ == case["psycopg_class"]
    assert error_class.sqlstate == case["code"]
    family: type[psycopg.Error] = getattr(psycopg, case["family"])
    assert issubclass(error_class, family)


@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_each_code_becomes_the_promised_storage_error(case: dict[str, Any]) -> None:
    translated = translate_storage_error(server_error(case), "contacts")

    assert (None if translated is None else type(translated).__name__) == case[
        "storage_error"
    ]
    if translated is not None:
        # The answer names the collection, never the server's row data.
        assert "slug_claims_pkey" not in str(translated)


@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_migrations_retry_exactly_the_documented_transient_codes(
    case: dict[str, Any],
) -> None:
    assert isinstance(server_error(case), RETRYABLE_ERRORS) is case["retried"]


@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_a_lock_wait_ends_on_the_documented_timeouts(case: dict[str, Any]) -> None:
    error: psycopg.Error = server_error(case)
    connection = LockConnection(error)

    with pytest.raises((ExternalServiceError, psycopg.Error)) as raised:
        acquire_lock(
            cast(PostgresConnection, connection),
            SESSION_LOCK,
            AdvisoryLockKey("booking:business_0000:2026-10-05"),
            LockWaitSeconds(5),
            deadline=0.0,
        )

    ended: bool = isinstance(raised.value, ExternalServiceError)
    assert ended is case["ends_lock_wait"]
    assert raised.value is not error if ended else raised.value is error
    assert connection.statements[-1] == SESSION_LOCK
