"""
Writers keep going while migration 1122 and its backfill run
(`uv run pytest -m perf tests/perf/test_migration_writer_stalls.py`;
PERF_SCALE=medium seeds 200,000 contacts and 200,000 bookings).

The database is migrated up to the file before 1122 and filled; four
threads then insert bookings and update contacts in short transactions
while the runner applies 1122 (columns, triggers, concurrent indexes) and
`workshop backfill-lookup` fills every new column. The longest single
write must stay under 2 s: the old pattern (a stored generated column and
a plain index in one transaction) blocked writes for the whole rewrite.
"""

from __future__ import annotations

import random
import shutil
import threading
import time
from collections.abc import Generator
from pathlib import Path

import psycopg
import pytest

from app.adapters.storage.postgres.postgres_lookup_backfill_adapter import (
    PostgresLookupBackfillAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.dto.lookup_backfill import BackfillLookupColumnsCommand
from app.use_cases.maintenance.backfill_lookup_columns_use_case import (
    BackfillLookupColumnsUseCase,
)
from tests.perf.perf_scale import read_scale
from tests.storage.migration_steps import run_migrations
from tests.storage.postgres_server import (
    ThrowawayPostgresServer,
    is_postgres_available,
    postgres_bin_directory,
)
from tests.storage.storage_testing import MIGRATIONS_DIRECTORY, RecordedRetryPause

pytestmark = pytest.mark.perf

FIRST_ONLINE_MIGRATION: str = "1122"
WRITER_THREADS: int = 4
LONGEST_STALL_SECONDS: float = 2.0
BUSINESSES: int = 50
SEED_SQL: str = """
select set_config('app.bypass_rls', 'on', false);
insert into workshop.contacts
    (document_key, business_id, document, created_at, updated_at)
select 'contact_' || n, 'business_' || (n % {businesses}),
    jsonb_build_object('id', 'contact_' || n,
        'business_id', 'business_' || (n % {businesses}),
        'name', 'Customer ' || n, 'created_at', n, 'updated_at', n,
        'last_seen_at', n, 'display_name_folded', 'customer ' || n,
        'channel_identities', '[]'::jsonb),
    n, n
from generate_series(1, {rows}) as n;
insert into workshop.bookings
    (document_key, business_id, document, created_at, updated_at)
select 'booking_' || n, 'business_' || (n % {businesses}),
    jsonb_build_object('id', 'booking_' || n,
        'business_id', 'business_' || (n % {businesses}),
        'contact_id', 'contact_' || n, 'status', 'confirmed', 'starts_at', n,
        'ends_at', n + 3600, 'created_at', n, 'source_channel', 'whatsapp'),
    n, n
from generate_series(1, {rows}) as n;
analyze workshop.contacts;
analyze workshop.bookings;
"""


@pytest.fixture(scope="module")
def postgres_server() -> Generator[ThrowawayPostgresServer]:
    bin_directory = postgres_bin_directory()
    if not is_postgres_available(bin_directory):
        pytest.skip(f"Postgres binaries not found in {bin_directory}.")

    server = ThrowawayPostgresServer(bin_directory)
    server.start()
    try:
        yield server
    finally:
        server.stop()


class Writers:
    """Threads writing in short transactions; the longest write is kept."""

    def __init__(self, server: ThrowawayPostgresServer, database: str, rows: int):
        self._server = server
        self._database = database
        self._rows = rows
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.longest_seconds: float = 0.0
        self.writes: int = 0
        self.errors: list[BaseException] = []
        self._threads = [
            threading.Thread(target=self._write, args=(index,))
            for index in range(WRITER_THREADS)
        ]

    def __enter__(self) -> Writers:
        for thread in self._threads:
            thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=60)

    def _write(self, index: int) -> None:
        generator = random.Random(index)  # noqa: S311 - test load, not security
        try:
            with self._server.app_connection(self._database) as connection:
                connection.execute("select set_config('app.bypass_rls', 'on', false)")
                sequence = 0
                while not self._stop.is_set():
                    sequence += 1
                    started = time.monotonic()
                    self._write_once(connection, generator, index, sequence)
                    self._record(time.monotonic() - started)
        except BaseException as error:  # noqa: BLE001 - reported by the test
            self.errors.append(error)

    def _write_once(
        self,
        connection: psycopg.Connection[tuple[object, ...]],
        generator: random.Random,
        index: int,
        sequence: int,
    ) -> None:
        key = f"live_{index}_{sequence}"
        with connection.transaction():
            connection.execute(
                "insert into workshop.bookings "
                "(document_key, business_id, document, created_at, updated_at) "
                "values (%s, 'business_1', jsonb_build_object('id', %s::text, "
                "'contact_id', 'contact_1', 'status', 'confirmed', "
                "'starts_at', 1, 'created_at', 1), 1, 1)",
                (key, key),
            )
            connection.execute(
                "update workshop.contacts set document = document || "
                "jsonb_build_object('last_seen_at', %s::bigint) "
                "where document_key = %s",
                (sequence, f"contact_{generator.randint(1, self._rows)}"),
            )

    def _record(self, seconds: float) -> None:
        with self._lock:
            self.writes += 1
            self.longest_seconds = max(self.longest_seconds, seconds)


def test_writers_never_stall_while_1122_and_its_backfill_run(
    postgres_server: ThrowawayPostgresServer,
    tmp_path: Path,
) -> None:
    rows: int = read_scale().messages
    database = postgres_server.create_database()
    database_url = postgres_server.app_database_url(database)
    earlier = tmp_path / "earlier"
    earlier.mkdir()
    for path in MIGRATIONS_DIRECTORY.glob("*.sql"):
        if path.name[:4] < FIRST_ONLINE_MIGRATION:
            shutil.copy(path, earlier / path.name)
    run_migrations(database_url, earlier)
    with postgres_server.app_connection(database) as connection:
        connection.execute(
            SEED_SQL.format(rows=rows, businesses=BUSINESSES).encode("utf-8")
        )

    pool = PostgresConnectionPoolClient(database_url, max_size=1)
    adapter = PostgresLookupBackfillAdapter(pool)
    with Writers(postgres_server, database, rows) as writers:
        time.sleep(0.5)
        report = run_migrations(database_url)
        backfill = BackfillLookupColumnsUseCase(
            backfill=adapter, retry_pause=RecordedRetryPause()
        ).run(BackfillLookupColumnsCommand())
        time.sleep(0.5)
    missing = {
        f"{column.collection_name}.{column.field}": int(adapter.count_missing(column))
        for column in adapter.list_trigger_columns()
    }
    pool.close()

    print(  # noqa: T201 - the numbers of the run (-s)
        f"{rows} rows: {writers.writes} writes, longest "
        f"{writers.longest_seconds:.3f} s while 1122 and its backfill ran; "
        f"{sum(int(entry.filled) for entry in backfill.columns)} rows backfilled"
    )
    assert writers.errors == []
    assert "1122_online_lookup_columns" in report.newly_applied
    assert set(missing.values()) == {0}, missing
    assert writers.writes > 100
    assert writers.longest_seconds < LONGEST_STALL_SECONDS, (
        f"a write waited {writers.longest_seconds:.2f} s"
    )
