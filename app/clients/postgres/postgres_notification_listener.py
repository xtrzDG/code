"""
One LISTEN session of a process on one Postgres notification channel: it
runs in a daemon thread, hands every payload to its handler, reconnects
with growing pauses, and tells its owner each time LISTEN is in place
again, because notifications sent while it was away are lost.

The cabinet's live events (`PostgresLiveEventListener`) and the job queue's
wake-ups (`PostgresJobWakeupAdapter`) each keep one.
"""

import logging
import threading
import time
from collections.abc import Callable

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow

from app.schemas.typings.platform.strings import DatabaseUrl

LOGGER: logging.Logger = logging.getLogger(__name__)

# How long one wait for notifications lasts; a stop request is noticed
# within this time.
NOTIFY_WAIT_SECONDS: float = 1.0
# A quiet connection is checked this often, so a dead one is replaced even
# when nothing is published (TCP keepalives catch the rest).
PROBE_INTERVAL_SECONDS: float = 30.0
RECONNECT_FIRST_DELAY_SECONDS: float = 0.5
RECONNECT_MAX_DELAY_SECONDS: float = 30.0
CONNECT_TIMEOUT_SECONDS: int = 10

type ListenerConnection = psycopg.Connection[TupleRow]
type ListenerConnector = Callable[[], ListenerConnection]


def connect_listener(
    database_url: DatabaseUrl,
    application_name: str,
) -> ListenerConnection:
    """A dedicated autocommit session with TCP keepalives (LISTEN needs a session)."""

    return psycopg.connect(
        str(database_url),
        autocommit=True,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
        application_name=application_name,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )


class PostgresNotificationListener:
    """
    Listens on `channel` in a thread named `thread_name` until stopped.
    `on_notification` gets each payload; `on_listening` runs every time
    LISTEN is (again) in place, so its owner can catch up on what it missed.
    Handlers run in the listener's thread and must not block for long.
    """

    def __init__(
        self,
        connect: ListenerConnector,
        channel: str,
        on_notification: Callable[[str], None],
        on_listening: Callable[[], None],
        thread_name: str,
        first_delay_seconds: float = RECONNECT_FIRST_DELAY_SECONDS,
        max_delay_seconds: float = RECONNECT_MAX_DELAY_SECONDS,
    ) -> None:
        self._connect: ListenerConnector = connect
        self._listen_statement: sql.Composed = sql.SQL("listen {}").format(
            sql.Identifier(channel)
        )
        self._channel: str = channel
        self._on_notification: Callable[[str], None] = on_notification
        self._on_listening: Callable[[], None] = on_listening
        self._thread_name: str = thread_name
        self._first_delay_seconds: float = first_delay_seconds
        self._max_delay_seconds: float = max_delay_seconds
        self._stop_event: threading.Event = threading.Event()
        self._lock: threading.Lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._is_listening: threading.Event = threading.Event()

    def ensure_started(self) -> None:
        """Start the thread once (later calls, and calls after stop, do nothing)."""

        with self._lock:
            if self._thread is not None or self._stop_event.is_set():
                return

            self._thread = threading.Thread(
                target=self.run, name=self._thread_name, daemon=True
            )
            self._thread.start()

    def wait_until_listening(self, timeout_seconds: float) -> bool:
        """True once LISTEN is in place (tests and startup checks)."""

        return self._is_listening.wait(timeout_seconds)

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._stop_event.set()
        with self._lock:
            thread: threading.Thread | None = self._thread

        if thread is not None:
            thread.join(timeout=timeout_seconds)

    def run(self) -> None:
        delay_seconds: float = self._first_delay_seconds
        while not self._stop_event.is_set():
            try:
                with self._connect() as connection:
                    connection.execute(self._listen_statement)
                    self._is_listening.set()
                    # Anything sent before LISTEN (or while away) is lost.
                    self._on_listening()
                    delay_seconds = self._first_delay_seconds
                    self._receive(connection)
            except psycopg.Error as error:
                LOGGER.warning(
                    "The %s listener lost its database connection (%s); "
                    "retrying in %.1f s",
                    self._channel,
                    type(error).__name__,
                    delay_seconds,
                )
            finally:
                self._is_listening.clear()

            if self._stop_event.wait(delay_seconds):
                return

            delay_seconds = min(delay_seconds * 2, self._max_delay_seconds)

    def _receive(self, connection: ListenerConnection) -> None:
        last_probe: float = time.monotonic()
        while not self._stop_event.is_set():
            for notification in connection.notifies(timeout=NOTIFY_WAIT_SECONDS):
                self._on_notification(notification.payload)

            if time.monotonic() - last_probe >= PROBE_INTERVAL_SECONDS:
                connection.execute("select 1")
                last_probe = time.monotonic()
