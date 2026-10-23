"""
A restore never brings a deleted business back: `workshop restore-check`
restores a backup taken before the deletions into a scratch database and
applies the deletion ledger to it, both its copy in the bucket (a business
deleted after the backup) and the restored database's own entries (a
deletion that was under way when the backup ran). What the law keeps
stays, and so does the job queue, where a deletion's own sub-processor
erasure jobs wait; the other business is restored whole.
"""

import json
from collections.abc import Generator

import pytest
from psycopg import sql
from typed_time_provider import Microseconds

from app.adapters.business_closures.bucket_deletion_ledger_mirror_adapter import (
    BucketDeletionLedgerMirrorAdapter,
)
from app.gateways.cli.backup_wiring import build_bucket
from app.schemas.dto.business_closures.deletion_ledger import DeletionLedgerRecord
from app.schemas.typings.backups.constrained_strings import BackupObjectPrefix
from app.schemas.typings.business_closures.prefixed_id import BusinessDeletionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.business_closures.retained_tables import outlives_deletion
from tests.compliance.moto_object_storage import moto_storage
from tests.storage.backup_drill_world import BackupDrillWorld
from tests.storage.postgres_server import (
    ThrowawayPostgresServer,
    postgres_bin_directory,
)

DELETED: BusinessId = BusinessId()
MID_DELETION: BusinessId = BusinessId()
KEPT: BusinessId = BusinessId()
ROWS: dict[str, int] = {
    "businesses": 1,
    "channels": 2,
    "contacts": 3,
    "invoices": 1,
    "queued_jobs": 1,
}
ERASED_PER_BUSINESS: int = sum(
    count
    for table, count in ROWS.items()
    if not outlives_deletion(DocumentCollectionName(table))
)
LEDGER_PREFIX: BackupObjectPrefix = BackupObjectPrefix("workshop/")


@pytest.fixture
def world(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> Generator[BackupDrillWorld]:
    with moto_storage() as storage:
        drill_world = BackupDrillWorld(postgres_server, database_name, storage)
        drill_world.environment["POSTGRES_CLIENT_BIN_DIRECTORY"] = str(
            postgres_bin_directory()
        )
        seed(postgres_server, database_name)
        yield drill_world


def seed(server: ThrowawayPostgresServer, database_name: str) -> None:
    """Three businesses' rows, and the ledger entry of a deletion under way."""

    with server.app_connection(database_name) as connection:
        for business_id in (DELETED, MID_DELETION, KEPT):
            for table, count in ROWS.items():
                for index in range(count):
                    connection.execute(
                        sql.SQL(
                            "insert into workshop.{} (document_key, business_id,"
                            " document, created_at, updated_at)"
                            " values (%s, %s, '{{}}', 1, 1)"
                        ).format(sql.Identifier(table)),
                        [f"{business_id}_{table}_{index}", str(business_id)],
                    )
        connection.execute(
            "insert into workshop.business_deletions (document_key, document,"
            " created_at, updated_at) values (%s, %s, 1, 1)",
            [
                str(BusinessDeletionId()),
                json.dumps({"deleted_business_id": str(MID_DELETION), "owners": []}),
            ],
        )


def mirror_deletion(world: BackupDrillWorld) -> None:
    """The deletion that started after the backup, as its job records it."""

    BucketDeletionLedgerMirrorAdapter(
        build_bucket(world.storage.connection()), LEDGER_PREFIX
    ).record(
        DeletionLedgerRecord(
            business_id=DELETED,
            deletion_id=BusinessDeletionId(),
            started_at=Microseconds(1_790_000_000_000_000),
        )
    )


def rows_by_business(
    server: ThrowawayPostgresServer, database: str
) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    with server.admin_connection(database) as connection:
        for table in ROWS:
            for business_id, count in connection.execute(
                sql.SQL(
                    "select business_id, count(*) from workshop.{} group by 1"
                ).format(sql.Identifier(table))
            ).fetchall():
                counts[(str(business_id), table)] = int(count)
    return counts


def test_a_restore_applies_the_deletion_ledger(
    world: BackupDrillWorld, postgres_server: ThrowawayPostgresServer
) -> None:
    assert world.backup().exit_code == 0
    mirror_deletion(world)

    drilled = world.restore_check("--keep-database")

    assert drilled.exit_code == 0, drilled.output + drilled.errors
    assert (
        f"Deletion ledger: 2 deleted businesses, {2 * ERASED_PER_BUSINESS} of "
        "their rows deleted again, 0 left." in drilled.output
    )
    [kept_database] = world.drill_databases()
    restored = rows_by_business(postgres_server, kept_database)
    postgres_server.drop_database(kept_database)
    for gone in (DELETED, MID_DELETION):
        assert {
            table: count
            for (business_id, table), count in restored.items()
            if business_id == str(gone)
        } == {"invoices": 1, "queued_jobs": 1}
    assert {
        table: count
        for (business_id, table), count in restored.items()
        if business_id == str(KEPT)
    } == ROWS


def test_a_foreign_ledger_object_fails_the_drill(world: BackupDrillWorld) -> None:
    assert world.backup().exit_code == 0
    world.put_object("workshop/deletion-ledger/unknown.json", b"{}")

    drilled = world.restore_check()

    assert drilled.exit_code == 1
    assert "is not a ledger record" in drilled.output + drilled.errors
    assert world.drill_databases() == []
