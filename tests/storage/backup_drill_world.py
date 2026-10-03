"""
A platform database with rows of two businesses, an S3 bucket (moto) and
the environment `workshop backup` and `workshop restore-check` read.
"""

import io
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import LiteralString

from psycopg import sql

from app.gateways.cli import backup, restore_check
from app.gateways.cli.backup_wiring import build_bucket
from app.gateways.cli.migrate import DEFAULT_MIGRATIONS_DIRECTORY
from app.schemas.typings.backups.constrained_strings import BackupObjectKey
from app.schemas.typings.platform.strings import LocalFilePath
from app.utilities.security.age.age_keys import recipient_of
from tests.backups.age_test_keys import generate_identity
from tests.compliance.moto_object_storage import (
    ACCESS_KEY_ID,
    REGION,
    SECRET_ACCESS_KEY,
    MotoStorage,
)
from tests.storage.postgres_server import ADMIN_ROLE_NAME, ThrowawayPostgresServer

ROWS: dict[str, dict[str, int]] = {
    "biz_alpha": {"businesses": 1, "channels": 3, "contacts": 4, "bookings": 2},
    "biz_bravo": {"businesses": 1, "channels": 2, "contacts": 1},
}

type Command = Callable[..., int]


@dataclass
class CommandRun:
    exit_code: int
    output: str
    errors: str


@dataclass(frozen=True)
class Snapshot:
    tables: int
    rows: int
    migrations: int
    secured_tables: int

    def line(self) -> str:
        return (
            f"Snapshot: {self.tables} tables, {self.rows} rows, "
            f"{self.migrations} migrations, {self.secured_tables} tables under "
            "row-level security."
        )


@dataclass
class BackupDrillWorld:
    server: ThrowawayPostgresServer
    database_name: str
    storage: MotoStorage

    def __post_init__(self) -> None:
        identity = generate_identity()
        self.environment: dict[str, str] = {
            "DATABASE_URL": str(self.server.app_database_url(self.database_name)),
            "BACKUP_S3_ENDPOINT_URL": self.storage.endpoint_url,
            "BACKUP_S3_REGION": REGION,
            "BACKUP_S3_BUCKET": self.storage.bucket,
            "BACKUP_S3_ACCESS_KEY_ID": ACCESS_KEY_ID,
            "BACKUP_S3_SECRET_ACCESS_KEY": SECRET_ACCESS_KEY,
            "BACKUP_AGE_PUBLIC_KEY": str(recipient_of(identity)),
            "BACKUP_AGE_IDENTITY": str(identity),
            "RESTORE_CHECK_DATABASE_URL": self.server.conninfo(
                "postgres", ADMIN_ROLE_NAME
            ),
        }

    def seed(self) -> None:
        with self.server.app_connection(self.database_name) as connection:
            connection.execute("select set_config('app.bypass_rls', 'on', false)")
            for business_id, tables in ROWS.items():
                for table, count in tables.items():
                    for index in range(count):
                        key = (
                            business_id if table == "businesses" else f"{table}_{index}"
                        )
                        connection.execute(
                            sql.SQL(
                                "insert into workshop.{} (document_key, business_id,"
                                " document, created_at, updated_at)"
                                " values (%s, %s, '{{}}', 1, 1)"
                            ).format(sql.Identifier(table)),
                            [f"{business_id}_{key}", business_id],
                        )

    def run_as_admin(self, statement: LiteralString) -> None:
        with self.server.admin_connection(self.database_name) as connection:
            connection.execute(statement)

    def backup(self, *arguments: str) -> CommandRun:
        return self._run(backup.main, list(arguments))

    def restore_check(self, *arguments: str) -> CommandRun:
        return self._run(restore_check.main, list(arguments))

    def put_object(self, key: str, content: bytes) -> None:
        """Replace an object of the bucket (as an attacker or a bug would)."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "object"
            path.write_bytes(content)
            build_bucket(self.storage.connection()).upload_file(
                BackupObjectKey(key), LocalFilePath(str(path))
            )

    def expected_snapshot(self) -> Snapshot:
        """What `workshop backup` should report, counted independently."""

        migrations = len(list(DEFAULT_MIGRATIONS_DIRECTORY.glob("*.sql")))
        seeded = sum(sum(tables.values()) for tables in ROWS.values())
        with self.server.admin_connection(self.database_name) as connection:
            row = connection.execute(
                "select count(*), count(*) filter (where c.relrowsecurity)"
                " from pg_class c join pg_namespace n on n.oid = c.relnamespace"
                " where n.nspname = 'workshop' and c.relkind in ('r', 'p')"
            ).fetchone()
        assert row is not None
        return Snapshot(int(row[0]), seeded + migrations, migrations, int(row[1]))

    def drill_databases(self) -> list[str]:
        with self.server.admin_connection() as connection:
            rows = connection.execute(
                "select datname from pg_database where datname like 'restore_drill%'"
                " order by datname"
            ).fetchall()
        return [str(row[0]) for row in rows]

    def _run(self, command: Command, arguments: list[str]) -> CommandRun:
        output, errors = io.StringIO(), io.StringIO()
        exit_code: int = command(arguments, self.environment, output, errors)
        return CommandRun(exit_code, output.getvalue(), errors.getvalue())
