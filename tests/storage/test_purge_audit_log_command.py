"""`workshop purge-audit-log` against a real Postgres and without one."""

import io
from collections.abc import Generator

import pytest
from typed_time_provider import Microseconds

from app.gateways.cli.purge_audit_log import main
from app.schemas.constants.compliance import AuditAction, AuditChainStatus
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.compliance.audit_chain.audit_chain_verification import (
    AuditChainVerification,
)
from app.utilities.compliance.audit_chain_hashing import PLATFORM_CHAIN_KEY
from tests.compliance.audit_chain.audit_entries import (
    START,
    TWO_YEARS_IN_MINUTES,
    entry,
)
from tests.storage.audit_chain_process import AuditProcess
from tests.storage.postgres_roles import RoleDatabase

# Entries are written two years before START: past any retention of a
# year, while the command's own RETENTION_PURGE entry (written now) is not.


@pytest.fixture
def process(role_urls: RoleDatabase) -> Generator[AuditProcess]:
    opened = AuditProcess(role_urls)
    try:
        yield opened
    finally:
        opened.close()


def test_the_command_purges_old_entries_and_the_chain_still_verifies(
    process: AuditProcess, role_urls: RoleDatabase
) -> None:
    for minute in range(5):
        process.log.append(
            entry(None, minute - TWO_YEARS_IN_MINUTES, action=AuditAction.LOGIN)
        )
    # As in production: the roles' addresses are set, the purge runs as
    # the migration role anyway.
    environment = role_urls.environment()
    output, again_output = io.StringIO(), io.StringIO()

    code = main(["--older-than-days", "365", "--batch", "2"], environment, output)
    again = main(["--older-than-days", "365"], environment, again_output)

    remaining = process.chains.entries_from(
        PLATFORM_CHAIN_KEY, AuditChainPosition(1), DocumentQueryLimit(50)
    )
    status = AuditChainVerification(process.chains).verify(
        PLATFORM_CHAIN_KEY, None, Microseconds(START)
    )
    assert (code, again) == (0, 0)
    assert output.getvalue() == "5 audit entries removed from 1 chains.\n"
    assert again_output.getvalue() == "0 audit entries removed from 0 chains.\n"
    (purge_entry,) = remaining
    assert purge_entry.action is AuditAction.RETENTION_PURGE
    assert purge_entry.chain_position == AuditChainPosition(6)
    assert int(purge_entry.record_count or 0) == 5
    assert status.status is AuditChainStatus.INTACT
    assert status.verified_through_position == AuditChainPosition(6)


def test_a_retention_shorter_than_a_year_is_refused() -> None:
    error_output = io.StringIO()

    code = main(
        ["--older-than-days", "30"],
        {"DATABASE_URL": "postgresql://unused.invalid/db"},
        error_output=error_output,
    )

    assert code == 2
    assert "at least 365 days" in error_output.getvalue()


def test_without_a_database_the_command_refuses() -> None:
    error_output = io.StringIO()

    assert main(["--older-than-days", "400"], {}, error_output=error_output) == 2
    assert "DATABASE_URL is not set" in error_output.getvalue()


def test_an_invalid_batch_exits_with_2() -> None:
    error_output = io.StringIO()

    code = main(
        ["--older-than-days", "400", "--batch", "0"], {}, error_output=error_output
    )

    assert code == 2
    assert "Invalid arguments" in error_output.getvalue()
