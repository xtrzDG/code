"""
`workshop backup` and `workshop restore-check` end to end: a real pg_dump
of a migrated database into an S3 bucket (moto) and a real pg_restore into
a scratch database of the throwaway server.
"""

import json
from collections.abc import Generator

import pytest

from tests.compliance.moto_object_storage import moto_storage
from tests.storage.backup_drill_world import BackupDrillWorld
from tests.storage.postgres_server import (
    ThrowawayPostgresServer,
    postgres_bin_directory,
)


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
        drill_world.seed()
        yield drill_world


def test_a_backup_restores_completely_and_isolates_businesses(
    world: BackupDrillWorld,
) -> None:
    backed_up = world.backup()

    assert backed_up.exit_code == 0, backed_up.errors
    assert "Snapshot: 53 tables, 31 rows, 17 migrations, 52 tables" in backed_up.output
    archives = [key for key in world.storage.object_keys() if key.endswith(".age")]
    assert len(archives) == 1
    manifest = json.loads(
        world.storage.raw_object(archives[0].replace(".pgdump.age", ".manifest.json"))
    )
    assert manifest["facts"]["row_counts"]["workshop.channels"] == 5
    assert b"biz_alpha" not in world.storage.raw_object(archives[0])

    drilled = world.restore_check()

    assert drilled.exit_code == 0, drilled.output + drilled.errors
    assert "row-level security probed on 52 tables" in drilled.output
    assert "OK: the backup restores completely" in drilled.output
    assert world.drill_databases() == []


def test_a_kept_restore_is_a_usable_database(
    world: BackupDrillWorld, postgres_server: ThrowawayPostgresServer
) -> None:
    assert world.backup().exit_code == 0

    drilled = world.restore_check("--keep-database")

    [kept] = world.drill_databases()
    assert f"into {kept} (kept)." in drilled.output
    with postgres_server.admin_connection(kept) as connection:
        rows = connection.execute(
            "select business_id, count(*) from workshop.contacts group by 1 order by 1"
        ).fetchall()
    assert rows == [("biz_alpha", 4), ("biz_bravo", 1)]
    postgres_server.drop_database(kept)


def test_a_manifest_that_disagrees_with_the_archive_fails_the_drill(
    world: BackupDrillWorld,
) -> None:
    assert world.backup().exit_code == 0
    [manifest_key] = [k for k in world.storage.object_keys() if k.endswith(".json")]
    manifest = json.loads(world.storage.raw_object(manifest_key))
    manifest["facts"]["row_counts"]["workshop.channels"] = 6
    world.put_object(manifest_key, json.dumps(manifest).encode())

    drilled = world.restore_check()

    assert drilled.exit_code == 1
    assert "FAILED  workshop.channels: 5 rows restored, 6 dumped." in drilled.output
    assert world.drill_databases() == []


def test_a_table_without_row_level_security_fails_the_drill(
    world: BackupDrillWorld,
) -> None:
    world.run_as_admin("alter table workshop.contacts disable row level security")
    world.run_as_admin("create policy leak on workshop.channels using (true)")
    assert world.backup().exit_code == 0

    drilled = world.restore_check()

    assert drilled.exit_code == 1
    assert (
        "FAILED  workshop.contacts: row-level security is off (a business table "
        "without it)." in drilled.output
    )
    assert (
        "FAILED  workshop.channels: 5 rows visible without a business scope."
        in drilled.output
    )
    assert (
        "FAILED  workshop.channels: 2 rows of other businesses visible in one "
        "business's scope." in drilled.output
    )


def test_a_backup_of_an_unreachable_database_fails(world: BackupDrillWorld) -> None:
    world.environment["DATABASE_URL"] = "host=/nonexistent port=1 dbname=x user=y"

    failed = world.backup()

    assert failed.exit_code == 1
    assert "Backup failed: The database could not be reached" in failed.errors
    assert world.storage.object_keys() == []
