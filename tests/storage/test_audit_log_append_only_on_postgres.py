"""
The audit log is append-only on Postgres (migrations 1193 and 1200): no
role that writes it (the application's tenant and platform roles, the
tables' owner) can change, delete or empty it, a tampered row is
found by the chain's check, the previous release keeps writing during
a deploy (its upsert still inserts; its count of a repeated view changes
nothing), and a chain's head left behind never forks the chain.
"""

from collections.abc import Generator
from typing import LiteralString

import psycopg
import pytest
from psycopg import errors

from app.schemas.constants.compliance import AuditAction, AuditChainProblem
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.compliance.audit_chain.audit_chain_verification import (
    AuditChainVerification,
)
from app.utilities.compliance.audit_chain_hashing import chain_key_of
from tests.compliance.audit_chain.audit_entries import entry
from tests.storage.audit_chain_process import AuditProcess
from tests.storage.postgres_roles import (
    PLATFORM_LOGIN_ROLE,
    TENANT_LOGIN_ROLE,
    RoleDatabase,
)
from tests.storage.postgres_server import APP_ROLE_NAME, ThrowawayPostgresServer
from tests.storage.storage_testing import build_fixed_wall_clock

BUSINESS: BusinessId = BusinessId()
CHANGE_COUNT: LiteralString = (
    "update workshop.audit_log_entries "
    "set document = jsonb_set(document, '{record_count}', '7') "
    "where document_key = %s"
)
# The previous release's write: an upsert (insert ... on conflict do update).
OLD_RELEASE_UPSERT: LiteralString = (
    "insert into workshop.audit_log_entries "
    "(document_key, business_id, document, created_at, updated_at) "
    "values (%s, %s, %s::jsonb, 1, 1) on conflict (document_key) do update set "
    "business_id = excluded.business_id, document = excluded.document, "
    "updated_at = excluded.updated_at"
)
# Every way the application's role could change a written entry; a `%s`
# takes the entry's key.
FORBIDDEN_CHANGES: tuple[LiteralString, ...] = (
    CHANGE_COUNT,
    "update workshop.audit_log_entries set created_at = 0",
    "delete from workshop.audit_log_entries where document_key = %s",
    "truncate workshop.audit_log_entries",
)


@pytest.fixture
def process(role_urls: RoleDatabase) -> Generator[AuditProcess]:
    opened = AuditProcess(role_urls)
    try:
        yield opened
    finally:
        opened.close()


@pytest.fixture(params=["owner", TENANT_LOGIN_ROLE, PLATFORM_LOGIN_ROLE])
def writer_role(
    request: pytest.FixtureRequest,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> Generator[psycopg.Connection[tuple[object, ...]]]:
    """
    A role that writes audit entries: the application's two roles, and the
    tables' owner (the previous release's role during a deploy).
    """

    role = APP_ROLE_NAME if request.param == "owner" else str(request.param)
    with psycopg.connect(
        postgres_server.conninfo(database_name, role), autocommit=True
    ) as connection:
        yield connection


@pytest.fixture
def app_role(
    postgres_server: ThrowawayPostgresServer, database_name: str
) -> Generator[psycopg.Connection[tuple[object, ...]]]:
    """The previous release's role (the tables' owner), seeing every business."""

    with postgres_server.app_connection(database_name) as connection:
        yield connection


def test_no_writer_role_can_change_delete_or_empty_entries(
    process: AuditProcess, writer_role: psycopg.Connection[tuple[object, ...]]
) -> None:
    stored = entry(BUSINESS)
    process.log.append(stored)

    for statement in FORBIDDEN_CHANGES:
        parameters = (str(stored.id),) if "%s" in statement else ()
        with pytest.raises(errors.InsufficientPrivilege):
            writer_role.execute(statement, parameters)

    assert process.entries.get(str(stored.id)) == process.chains.head_of(
        chain_key_of(BUSINESS)
    )


def test_the_previous_release_still_writes_and_its_view_counts_change_nothing(
    process: AuditProcess, app_role: psycopg.Connection[tuple[object, ...]]
) -> None:
    viewed = entry(BUSINESS, action=AuditAction.VIEW, actor=UserId())
    process.log.append(viewed)
    chained = process.entries.get(str(viewed.id))
    old_entry = entry(BUSINESS, 1)
    old_document = old_entry.model_dump_json()

    app_role.execute(
        OLD_RELEASE_UPSERT, (str(old_entry.id), str(BUSINESS), old_document)
    )
    app_role.execute(CHANGE_COUNT, (str(viewed.id),))

    assert process.entries.get(str(viewed.id)) == chained
    written = process.entries.get(str(old_entry.id))
    assert written is not None
    assert written.chain_key is None


def test_a_row_changed_behind_the_application_is_found(
    process: AuditProcess,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    for minute in range(4):
        process.log.append(entry(BUSINESS, minute))
    (third,) = process.chains.entries_from(
        chain_key_of(BUSINESS), AuditChainPosition(3), DocumentQueryLimit(1)
    )

    tamper_as_superuser(postgres_server, database_name, third)
    status = AuditChainVerification(process.chains).verify(
        chain_key_of(BUSINESS), None, build_fixed_wall_clock().now_unix()
    )

    assert status.problem is AuditChainProblem.HASH_MISMATCH
    assert status.broken_position == third.chain_position


def test_a_head_left_behind_never_forks_the_chain(process: AuditProcess) -> None:
    for minute in range(3):
        process.log.append(entry(BUSINESS, minute))
    chain_key = chain_key_of(BUSINESS)
    first, _, third = process.chains.entries_from(
        chain_key, AuditChainPosition(1), DocumentQueryLimit(3)
    )
    head = process.heads.get(str(chain_key))
    assert head is not None
    assert first.chain_position is not None
    assert first.entry_hash is not None
    process.heads.upsert(
        str(chain_key),
        head.model_copy(
            update={
                "head_position": first.chain_position,
                "head_hash": first.entry_hash,
            }
        ),
    )

    fourth = entry(BUSINESS, 3)
    process.log.append(fourth)

    appended = process.entries.get(str(fourth.id))
    assert appended is not None
    assert appended.chain_position == AuditChainPosition(4)
    assert appended.prev_hash == third.entry_hash
    moved = process.heads.get(str(chain_key))
    assert moved is not None
    assert moved.head_position == AuditChainPosition(4)


def tamper_as_superuser(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    stored: AuditLogEntryDocument,
) -> None:
    """Someone with the database's superuser switches the guard off."""

    with postgres_server.admin_connection(database_name) as connection:
        connection.execute("set session_replication_role = replica")
        connection.execute(CHANGE_COUNT, (str(stored.id),))
