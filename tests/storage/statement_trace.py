"""
What a block of code costs the database, as the server sees it: libpq's
protocol trace of every connection of a pool (`PGconn.trace`), counted.

- A round trip is one exchange the client waits for: a simple query (one
  message, however many statements it carries: `begin; select
  set_config(...)` is one) or an extended-protocol statement up to its
  Sync. The server answers each with exactly one ReadyForQuery, so the
  round trips are the ReadyForQuery messages.
- A transaction ends whenever a ReadyForQuery reports the session idle
  again ('I'): a COMMIT or ROLLBACK, or a statement outside a transaction
  block (its own transaction).

The trace sees everything the application sends, psycopg's own BEGIN,
SAVEPOINT and COMMIT included, so the counts are deterministic: unlike
timings, they do not depend on how busy the machine is.
"""

import re
import tempfile
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from psycopg import pq

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.schemas.typings.platform.strings import DatabaseUrl

# "B	5	ReadyForQuery	 I" in the trace (regress mode, no timestamps).
READY_FOR_QUERY: re.Pattern[str] = re.compile(r"^B\t\d+\tReadyForQuery\t (\w)$")
TRACE_FLAGS: pq.Trace = pq.Trace.SUPPRESS_TIMESTAMPS | pq.Trace.REGRESS_MODE


@dataclass
class TraceCount:
    """What one traced block sent: round trips and transactions ended."""

    round_trips: int = 0
    transactions: int = 0


class TracedConnectionPool(PostgresConnectionPoolClient):
    """
    The application's pool, whose connections can be traced: `traced()`
    traces every connection (open or opened during the block) into files
    of a temporary directory and counts them when the block ends.
    """

    def __init__(self, database_url: DatabaseUrl, max_size: int) -> None:
        super().__init__(database_url, max_size=max_size)
        self._trace_lock: threading.Lock = threading.Lock()
        self._traced: list[PostgresConnection] = []
        self._trace_directory: Path | None = None
        self._trace_files: list[IO[str]] = []

    def _open_new_connection(self) -> PostgresConnection:
        connection: PostgresConnection = super()._open_new_connection()
        with self._trace_lock:
            self._traced.append(connection)
            if self._trace_directory is not None:
                self._trace_files.append(start_trace(connection, self._trace_directory))
        return connection

    @contextmanager
    def traced(self) -> Generator[TraceCount]:
        count = TraceCount()
        with tempfile.TemporaryDirectory(prefix="workshop-trace-") as directory:
            with self._trace_lock:
                self._trace_directory = Path(directory)
                self._trace_files = [
                    start_trace(connection, self._trace_directory)
                    for connection in self._traced
                    if not connection.closed
                ]
            try:
                yield count
            finally:
                with self._trace_lock:
                    for connection in self._traced:
                        if not connection.closed:
                            # Flushes what libpq buffered for the file.
                            connection.pgconn.untrace()
                    files: list[IO[str]] = self._trace_files
                    self._trace_directory, self._trace_files = None, []
                for trace_file in files:
                    trace_file.close()
                    add_counts(count, Path(trace_file.name).read_text())


def start_trace(connection: PostgresConnection, directory: Path) -> IO[str]:
    trace_file: IO[str] = tempfile.NamedTemporaryFile(  # noqa: SIM115 - closed by traced()
        "w", dir=directory, suffix=".trace", delete=False
    )
    connection.pgconn.trace(trace_file.fileno())
    connection.pgconn.set_trace_flags(TRACE_FLAGS)
    return trace_file


def add_counts(count: TraceCount, trace_text: str) -> None:
    for line in trace_text.splitlines():
        ready = READY_FOR_QUERY.match(line)
        if ready is None:
            continue

        count.round_trips += 1
        if ready.group(1) == "I":
            count.transactions += 1
