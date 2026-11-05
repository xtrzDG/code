"""
Purging an audit chain on Postgres (`workshop.purge_audit_chain`, 1193):
the oldest entries go with a checkpoint that keeps the chain verifiable,
the application still cannot delete one by itself, and the next entry
links to the checkpoint; the anomaly counts and the platform's pages are
computed by the database.
"""

from collections.abc import Generator

import psycopg
import pytest
from psycopg import errors
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import (
    AuditAction,
    AuditChainStatus,
    AuditSecurityEvent,
)
from app.schemas.dto.audit_trail import PlatformAuditFilter
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainPosition,
    AuditPurgeBatchSize,
)
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.alerts.audit_alert_checks import ADMIN_TENANT_ACTIONS
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
from tests.storage.audit_chain_process import AuditProcess
from tests.storage.postgres_roles import RoleDatabase
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import build_fixed_wall_clock

BUSINESS: BusinessId = BusinessId()
OTHER: BusinessId = BusinessId()


@pytest.fixture
def process(role_urls: RoleDatabase) -> Generator[AuditProcess]:
    opened = AuditProcess(role_urls)
    try:
        yield opened
    finally:
        opened.close()


def test_a_purge_leaves_a_checkpoint_the_chain_goes_on_from(
    process: AuditProcess,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    chain = chain_key_of(BUSINESS)
    for minute in range(6):
        process.log.append(entry(BUSINESS, minute - TWO_YEARS_IN_MINUTES))
    verification = AuditChainVerification(process.chains)
    now = build_fixed_wall_clock().now_unix()
    before = verification.verify(chain, None, now)
    cutoff = Microseconds(START + (4 - TWO_YEARS_IN_MINUTES) * MINUTE)

    removed = [
        process.purges.purge(chain, cutoff, AuditPurgeBatchSize(3)) for _ in range(3)
    ]
    process.log.append(entry(BUSINESS, 7))
    after = verification.verify(chain, before, now)

    assert [int(count) for count in removed] == [3, 1, 0]
    checkpoint = process.chains.checkpoint_of(chain)
    assert checkpoint is not None
    assert checkpoint.through_position == AuditChainPosition(4)
    assert int(checkpoint.purged_count) == 4
    assert checkpoint.purged_before == cutoff
    assert after.status is AuditChainStatus.INTACT
    assert after.verified_through_position == AuditChainPosition(7)
    with (
        postgres_server.app_connection(database_name) as connection,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        connection.execute("delete from workshop.audit_log_entries")


def test_a_purge_refuses_a_chain_that_is_no_chain(process: AuditProcess) -> None:
    with (
        process.owner_pool.transaction() as connection,
        pytest.raises(psycopg.errors.InvalidParameterValue),
    ):
        connection.execute("select workshop.purge_audit_chain('users', 0, 10)")


def test_the_hours_anomaly_counts_come_from_the_database(
    process: AuditProcess,
) -> None:
    admin = UserId()
    for minute in range(3):
        process.log.append(entry(BUSINESS, minute, action=AuditAction.EXPORT))
    process.log.append(entry(BUSINESS, 3, action=AuditAction.DELETE, entity="contact"))
    process.log.append(
        entry(BUSINESS, 3, action=AuditAction.DELETE, entity="quick_reply")
    )
    for business in (BUSINESS, OTHER):
        process.log.append(
            entry(business, 4, action=AuditAction.ADMIN_ACCESS, actor=admin)
        )
    for minute in range(2):
        failed = entry(
            None, minute, action=AuditAction.LOGIN, entity="login_destination"
        )
        process.log.append(
            failed.model_copy(
                update={
                    "security_event": AuditSecurityEvent.LOGIN_FAILED,
                    "entity_id": AuditEntityReference("dest_0123"),
                }
            )
        )
    since = Microseconds(START)

    operations = process.activity.count_personal_data_operations(since)
    tenants = process.activity.count_tenants_by_admin(since, ADMIN_TENANT_ACTIONS)
    failures = process.activity.count_failed_checks(since)
    page = process.activity.page_platform_entries(
        KeysetSlice(limit=KeysetReadLimit(10)),
        PlatformAuditFilter(security_event=AuditSecurityEvent.LOGIN_FAILED),
    )

    assert [(item.business_id, int(item.operation_count)) for item in operations] == [
        (BUSINESS, 4)
    ]
    assert [(item.actor_id, int(item.business_count)) for item in tenants] == [
        (admin, 2)
    ]
    assert [(str(item.entity_id), int(item.failure_count)) for item in failures] == [
        ("dest_0123", 2)
    ]
    assert [int(item.chain_position or 0) for item in page] == [2, 1]
