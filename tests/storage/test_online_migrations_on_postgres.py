"""
The online-safe runner against a real Postgres: a file that waits for a
busy table's lock gives up after `lock_timeout` and is tried again, and a
no-transaction file builds indexes concurrently, rebuilds the ones a failed
try left invalid and is recorded only after its last statement.
"""

import threading
from pathlib import Path

import pytest
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.postgres_schema_migration_store_adapter import (
    PostgresSchemaMigrationStoreAdapter,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.dto.storage import (
    ApplyDatabaseMigrationsCommand,
    DatabaseMigrationsReport,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.storage.constrained_integers import (
    LockWaitSeconds,
    MigrationAttemptLimit,
    MigrationAttemptNumber,
)
from app.use_cases.maintenance.apply_database_migrations_use_case import (
    ApplyDatabaseMigrationsUseCase,
)
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import RecordedRetryPause, build_fixed_wall_clock

CREATE_TABLE: str = "create table workshop.busy (id bigint not null, note text);\n"
NO_TRANSACTION: str = "-- 0002_index\n--\n-- workshop:no-transaction\n"


class ReleasingRetryPause(RecordedRetryPause):
    """Records the pauses and lets the blocking transaction end at the first."""

    def __init__(self, release: threading.Event, released: threading.Event) -> None:
        super().__init__()
        self._release: threading.Event = release
        self._released: threading.Event = released

    def pause(self, attempt: MigrationAttemptNumber) -> None:
        super().pause(attempt)
        self._release.set()
        assert self._released.wait(timeout=10)


def write_migrations(directory: Path, files: dict[str, str]) -> Path:
    directory.mkdir(exist_ok=True)
    for name, sql_text in files.items():
        (directory / f"{name}.sql").write_text(sql_text, encoding="utf-8")

    return directory


def migrate(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    directory: Path,
    pause: RecordedRetryPause | None = None,
) -> DatabaseMigrationsReport:
    connection_pool = PostgresConnectionPoolClient(
        postgres_server.app_database_url(database_name), max_size=1
    )
    try:
        return ApplyDatabaseMigrationsUseCase(
            migration_source=SqlFileMigrationSourceAdapter(directory),
            migration_store=PostgresSchemaMigrationStoreAdapter(
                connection_pool, lock_timeout=LockWaitSeconds(1)
            ),
            wall_clock=build_fixed_wall_clock(),
            retry_pause=pause or RecordedRetryPause(),
            attempt_limit=MigrationAttemptLimit(3),
        ).run(ApplyDatabaseMigrationsCommand())
    finally:
        connection_pool.close()


def query(
    postgres_server: ThrowawayPostgresServer, database_name: str, sql_text: str
) -> list[TupleRow]:
    with postgres_server.admin_connection(database_name) as connection:
        return connection.execute(sql_text.encode("utf-8")).fetchall()


def test_a_file_blocked_by_a_long_transaction_is_tried_again(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    directory = write_migrations(
        tmp_path / "migrations",
        {"0001_table": "create schema if not exists workshop;\n" + CREATE_TABLE},
    )
    migrate(postgres_server, empty_database_name, directory)
    write_migrations(
        directory, {"0002_column": "alter table workshop.busy add column extra text;"}
    )
    release, released, holding = threading.Event(), threading.Event(), threading.Event()

    def hold_the_table() -> None:
        with (
            postgres_server.app_connection(empty_database_name) as connection,
            connection.transaction(),
        ):
            connection.execute("lock table workshop.busy in access share mode")
            holding.set()
            release.wait(timeout=30)
        released.set()

    blocker = threading.Thread(target=hold_the_table)
    blocker.start()
    assert holding.wait(timeout=10)
    pause = ReleasingRetryPause(release, released)
    try:
        report = migrate(postgres_server, empty_database_name, directory, pause)
    finally:
        release.set()
        blocker.join(timeout=30)

    assert report.newly_applied == ["0002_column"]
    assert pause.attempts == [1]
    columns = query(
        postgres_server,
        empty_database_name,
        "select column_name from information_schema.columns "
        "where table_name = 'busy' order by column_name",
    )
    assert [row[0] for row in columns] == ["extra", "id", "note"]


def test_a_no_transaction_file_builds_its_index_concurrently(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    directory = write_migrations(
        tmp_path / "migrations",
        {
            "0001_table": "create schema if not exists workshop;\n" + CREATE_TABLE,
            "0002_index": NO_TRANSACTION
            + "alter table workshop.busy add column if not exists lookup bigint;\n"
            + "create index concurrently if not exists busy_lookup_idx\n"
            + "    on workshop.busy (lookup);\n",
        },
    )

    report = migrate(postgres_server, empty_database_name, directory)
    again = migrate(postgres_server, empty_database_name, directory)

    assert report.newly_applied == ["0001_table", "0002_index"]
    assert again.already_applied == ["0001_table", "0002_index"]
    assert query(
        postgres_server,
        empty_database_name,
        "select i.indisvalid from pg_index i join pg_class c on c.oid = i.indexrelid "
        "where c.relname = 'busy_lookup_idx'",
    ) == [(True,)]


def test_an_invalid_index_of_a_failed_try_is_dropped_and_rebuilt(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    directory = write_migrations(
        tmp_path / "migrations",
        {
            "0001_table": "create schema if not exists workshop;\n"
            + CREATE_TABLE
            + "insert into workshop.busy (id) values (1), (1), (2);\n",
            "0002_index": NO_TRANSACTION
            + "create unique index concurrently if not exists busy_id_key\n"
            + "    on workshop.busy (id);\n",
        },
    )

    with pytest.raises(ExternalServiceError, match="0002_index"):
        migrate(postgres_server, empty_database_name, directory)

    index_state = (
        "select i.indisvalid from pg_index i join pg_class c on c.oid = i.indexrelid "
        "where c.relname = 'busy_id_key'"
    )
    recorded = "select name from workshop.schema_migrations order by name"
    assert query(postgres_server, empty_database_name, index_state) == [(False,)]
    assert query(postgres_server, empty_database_name, recorded) == [("0001_table",)]
    query(
        postgres_server,
        empty_database_name,
        "delete from workshop.busy where ctid = (select max(ctid) from workshop.busy "
        "where id = 1) returning id",
    )

    report = migrate(postgres_server, empty_database_name, directory)

    assert report.newly_applied == ["0002_index"]
    assert query(postgres_server, empty_database_name, index_state) == [(True,)]
    assert query(postgres_server, empty_database_name, recorded) == [
        ("0001_table",),
        ("0002_index",),
    ]


def test_no_transaction_files_leave_no_session_state_behind(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    directory = write_migrations(
        tmp_path / "migrations",
        {
            "0001_table": NO_TRANSACTION
            + "create schema if not exists workshop;\n"
            + "create table if not exists workshop.busy (id bigint);\n"
        },
    )
    connection_pool = PostgresConnectionPoolClient(
        postgres_server.app_database_url(empty_database_name), max_size=1
    )
    try:
        PostgresSchemaMigrationStoreAdapter(connection_pool).apply_if_pending(
            SqlFileMigrationSourceAdapter(directory).load_scripts()[0],
            build_fixed_wall_clock().now_unix(),
        )
        with connection_pool.connection() as connection:
            settings = connection.execute(
                "select current_setting('lock_timeout'), "
                "(select count(*) from pg_locks where locktype = 'advisory' "
                "and pid = pg_backend_pid())"
            ).fetchone()
    finally:
        connection_pool.close()

    assert settings == ("0", 0)
