"""
A restore counts the erased customers it brings back: `workshop
restore-check` restores a backup taken before an erasure, reads the erasure
ledger in the bucket and reports how many of its customers the backup
holds with their data again (the daily job erases them again after a real
restore); one erased before the backup counts as erased.
"""

import json
from collections.abc import Generator

import pytest
from typed_time_provider import Microseconds

from app.adapters.business_closures.bucket_contact_erasure_ledger_adapter import (
    BucketContactErasureLedgerAdapter,
)
from app.gateways.cli.backup_wiring import build_bucket
from app.schemas.dto.business_closures.contact_erasure_ledger import (
    ContactErasureRecord,
)
from app.schemas.typings.backups.constrained_strings import BackupObjectPrefix
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from tests.compliance.moto_object_storage import moto_storage
from tests.storage.backup_drill_world import BackupDrillWorld
from tests.storage.postgres_server import (
    ThrowawayPostgresServer,
    postgres_bin_directory,
)

BUSINESS: BusinessId = BusinessId()
ERASED_AFTER_BACKUP: ContactId = ContactId()
ERASED_BEFORE_BACKUP: ContactId = ContactId()
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
    """The business and two customers: one still whole, one erased already."""

    with server.app_connection(database_name) as connection:
        connection.execute(
            "insert into workshop.businesses (document_key, business_id, document,"
            " created_at, updated_at) values (%s, %s, '{}', 1, 1)",
            [str(BUSINESS), str(BUSINESS)],
        )
        for contact_id, document in (
            (ERASED_AFTER_BACKUP, {"name": "Giulia"}),
            (ERASED_BEFORE_BACKUP, {"erased_at": 1_780_000_000_000_000}),
        ):
            connection.execute(
                "insert into workshop.contacts (document_key, business_id,"
                " document, created_at, updated_at) values (%s, %s, %s, 1, 1)",
                [str(contact_id), str(BUSINESS), json.dumps(document)],
            )


def test_the_drill_counts_the_erased_customers_a_backup_brings_back(
    world: BackupDrillWorld,
) -> None:
    assert world.backup().exit_code == 0
    ledger = BucketContactErasureLedgerAdapter(
        build_bucket(world.storage.connection()), LEDGER_PREFIX
    )
    for contact_id, erased_at in (
        (ERASED_BEFORE_BACKUP, 1_780_000_000_000_000),
        (ERASED_AFTER_BACKUP, 1_790_000_000_000_000),
    ):
        ledger.record(
            ContactErasureRecord(
                business_id=BUSINESS,
                contact_id=contact_id,
                erased_at=Microseconds(erased_at),
            )
        )

    drilled = world.restore_check()

    assert drilled.exit_code == 0, drilled.output + drilled.errors
    assert (
        "Erasure ledger: 2 erased customers, 1 of them with their data in this "
        "backup" in drilled.output
    )
    assert "Deletion ledger: 0 deleted businesses" in drilled.output
    assert world.drill_databases() == []
