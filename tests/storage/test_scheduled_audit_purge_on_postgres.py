"""
The daily audit purge on Postgres (`workshop.purge_expired_audit_chain`,
1250): the platform role may call it and it removes only entries past the
1,095-day retention by the database's clock, whatever cutoff it is asked
for; the tenant role may not call it, and the platform role still may not
call the operator's `workshop.purge_audit_chain`.
"""

from collections.abc import Generator
from typing import LiteralString

import psycopg
import pytest
from psycopg import errors
from typed_time_provider import Microseconds

from app.adapters.compliance.postgres_audit_chain_purge_adapter import (
    RETENTION_PURGE_STATEMENT,
    PostgresAuditChainPurgeAdapter,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainPosition,
    AuditPurgeBatchSize,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.compliance.audit_chain_hashing import chain_key_of
from tests.compliance.audit_chain.audit_entries import MINUTE, START, entry
from tests.storage.audit_chain_process import AuditProcess
from tests.storage.postgres_roles import (
    PLATFORM_LOGIN_ROLE,
    TENANT_LOGIN_ROLE,
    RoleDatabase,
)
from tests.storage.postgres_server import ThrowawayPostgresServer

BUSINESS: BusinessId = BusinessId()
DAY_IN_MINUTES: int = 24 * 60
# START lies a few weeks around today: four years before it is past the
# retention, two years before it is not (but past the 365-day floor).
FOUR_YEARS_AGO: int = -4 * 365 * DAY_IN_MINUTES
TWO_YEARS_AGO: int = -2 * 365 * DAY_IN_MINUTES
CALL: LiteralString = "select workshop.purge_expired_audit_chain(%s, %s, %s)"
OPERATORS_CALL: LiteralString = "select workshop.purge_audit_chain(%s, %s, %s)"


@pytest.fixture
def process(role_urls: RoleDatabase) -> Generator[AuditProcess]:
    opened = AuditProcess(role_urls)
    try:
        yield opened
    finally:
        opened.close()


def test_the_platform_role_purges_only_what_is_past_the_retention(
    process: AuditProcess,
) -> None:
    chain = chain_key_of(BUSINESS)
    for minute in range(3):
        process.log.append(entry(BUSINESS, FOUR_YEARS_AGO + minute))
    for minute in range(2):
        process.log.append(entry(BUSINESS, TWO_YEARS_AGO + minute))
    purges = PostgresAuditChainPurgeAdapter(
        process.pools.platform, RETENTION_PURGE_STATEMENT
    )
    # Asked for everything older than a year and a half: the database keeps
    # what is younger than 1,095 days anyway.
    asked = Microseconds(START - 540 * DAY_IN_MINUTES * MINUTE)

    removed = [purges.purge(chain, asked, AuditPurgeBatchSize(2)) for _ in range(3)]

    left = process.chains.entries_from(
        chain, AuditChainPosition(1), DocumentQueryLimit(10)
    )
    checkpoint = process.chains.checkpoint_of(chain)
    assert [int(count) for count in removed] == [2, 1, 0]
    assert [int(stored.chain_position or 0) for stored in left] == [4, 5]
    assert checkpoint is not None
    assert checkpoint.through_position == AuditChainPosition(3)
    assert int(checkpoint.purged_before) < int(asked)


def test_the_tenant_role_may_not_call_the_daily_purge(
    postgres_server: ThrowawayPostgresServer, database_name: str
) -> None:
    with (
        psycopg.connect(
            postgres_server.conninfo(database_name, TENANT_LOGIN_ROLE),
            autocommit=True,
        ) as tenant,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        tenant.execute(CALL, (str(chain_key_of(BUSINESS)), 0, 10))


def test_the_platform_role_still_may_not_call_the_operators_purge(
    postgres_server: ThrowawayPostgresServer, database_name: str
) -> None:
    with (
        psycopg.connect(
            postgres_server.conninfo(database_name, PLATFORM_LOGIN_ROLE),
            autocommit=True,
        ) as platform,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        platform.execute(OPERATORS_CALL, (str(chain_key_of(BUSINESS)), 0, 10))
