"""
The guards around purging an audit chain on Postgres (migration 1193):
the purge function refuses a cutoff younger than a year, whoever calls it;
only the purge function may delete entries, even for a role that holds
DELETE and switches the purge setting on; and a purge that commits while
the daily check runs is no break.
"""

import uuid
from collections.abc import Generator
from typing import LiteralString

import psycopg
import pytest
from psycopg import errors, sql
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditChainStatus
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainPosition,
    AuditPurgeBatchSize,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.compliance.audit_chain.audit_chain_verification import (
    AuditChainVerification,
)
from app.utilities.compliance.audit_chain_hashing import chain_key_of
from tests.compliance.audit_chain.audit_entries import (
    MINUTE,
    START,
    TWO_YEARS_IN_MINUTES,
    entry,
)
from tests.compliance.audit_chain.purge_mid_check import PurgeBeforeEntryRead
from tests.storage.audit_chain_process import AuditProcess
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import build_fixed_wall_clock

pytestmark = pytest.mark.postgres
BUSINESS: BusinessId = BusinessId()
PLATFORM_WIDE: LiteralString = "select set_config('app.bypass_rls', 'on', false)"
PURGE: LiteralString = "select workshop.purge_audit_chain(%s, %s, %s)"
PURGE_SETTING_ON: LiteralString = (
    "select set_config('workshop.audit_chain_purge', 'on', false)"
)
# Far in the future: every entry was written before it.
EVERYTHING: int = 9_000_000_000_000_000_000


@pytest.fixture
def process(database_url: DatabaseUrl) -> Generator[AuditProcess]:
    opened = AuditProcess(database_url)
    try:
        yield opened
    finally:
        opened.close()


def stored_count(process: AuditProcess) -> int:
    return len(
        process.chains.entries_from(
            chain_key_of(BUSINESS), AuditChainPosition(1), DocumentQueryLimit(100)
        )
    )


def test_the_application_role_cannot_purge_entries_of_the_last_year(
    process: AuditProcess,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    for minute in range(5):
        process.log.append(entry(BUSINESS, minute))
    chain = chain_key_of(BUSINESS)
    now = build_fixed_wall_clock().now_unix()
    verified = AuditChainVerification(process.chains).verify(chain, None, now)

    with (
        postgres_server.app_connection(database_name) as app,
        pytest.raises(errors.InvalidParameterValue, match="at least 365 days"),
    ):
        app.execute(PLATFORM_WIDE)
        app.execute(PURGE, (str(chain), EVERYTHING, 1_000))

    assert stored_count(process) == 5
    assert process.chains.checkpoint_of(chain) is None
    again = AuditChainVerification(process.chains).verify(chain, verified, now)
    assert again.status is AuditChainStatus.INTACT
    with pytest.raises(ValidationFailedError, match="at least 365 days"):
        process.purges.purge(chain, Microseconds(EVERYTHING), AuditPurgeBatchSize(10))


def test_a_role_with_delete_and_the_purge_setting_still_cannot_delete(
    process: AuditProcess,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    for minute in range(2):
        process.log.append(entry(BUSINESS, minute))
    role = f"audit_tenant_{uuid.uuid4().hex[:8]}"
    with postgres_server.admin_connection(database_name) as admin:
        admin.execute(
            sql.SQL("create role {} login nosuperuser nobypassrls").format(
                sql.Identifier(role)
            )
        )
        admin.execute(
            sql.SQL("grant usage on schema workshop to {}").format(sql.Identifier(role))
        )
        admin.execute(
            sql.SQL("grant select, delete on workshop.audit_log_entries to {}").format(
                sql.Identifier(role)
            )
        )

    with (
        psycopg.connect(
            postgres_server.conninfo(database_name, role), autocommit=True
        ) as tenant,
        pytest.raises(errors.InsufficientPrivilege, match="purge_audit_chain"),
    ):
        tenant.execute(PLATFORM_WIDE)
        tenant.execute(PURGE_SETTING_ON)
        tenant.execute("delete from workshop.audit_log_entries")

    assert stored_count(process) == 2


def test_a_purge_committed_while_the_check_runs_is_no_break(
    process: AuditProcess,
) -> None:
    chain = chain_key_of(BUSINESS)
    for minute in range(6):
        process.log.append(entry(BUSINESS, minute - TWO_YEARS_IN_MINUTES))
    now = build_fixed_wall_clock().now_unix()
    previous = AuditChainVerification(process.chains).verify(chain, None, now)
    for minute in range(6, 8):
        process.log.append(entry(BUSINESS, minute - TWO_YEARS_IN_MINUTES))
    cutoff = Microseconds(START + (6 - TWO_YEARS_IN_MINUTES) * MINUTE)
    # The purge of entries 1-6 (the newest one the last check verified among
    # them) commits after the check read the checkpoint, before it looks
    # for that entry.
    racing = PurgeBeforeEntryRead(
        process.chains,
        read_number=1,
        commit_purge=lambda: process.purges.purge(
            chain, cutoff, AuditPurgeBatchSize(100)
        ),
    )

    status = AuditChainVerification(racing).verify(chain, previous, now)

    assert status.status is AuditChainStatus.INTACT
    assert status.verified_through_position == AuditChainPosition(8)
