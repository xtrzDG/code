"""
The one LISTEN connection of an API process: it hears every live event
published by any process (API instances, workers) and hands it to the
process's fan-out. It runs in a daemon thread, reconnects with growing
pauses, and asks every open stream to resync after a reconnect, because
events published while it was away are lost.
"""

import logging
import threading
import time
from collections.abc import Callable
from typing import LiteralString

import psycopg
from psycopg.rows import TupleRow
from pydantic import ValidationError

from app.adapters.events.live_event_fanout import LiveEventFanout
from app.schemas.dto.live_events import LiveEvent
from app.schemas.typings.platform.strings import DatabaseUrl

LOGGER: logging.Logger = logging.getLogger(__name__)

LIVE_EVENTS_CHANNEL: LiteralString = "workshop_live_events"
LISTEN_STATEMENT: LiteralString = f"listen {LIVE_EVENTS_CHANNEL}"
LISTENER_APPLICATION_NAME: str = "assistant-workshop-live-events"
LISTENER_THREAD_NAME: str = "live-event-listener"
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


def connect_listener(database_url: DatabaseUrl) -> ListenerConnection:
    """A dedicated autocommit session with TCP keepalives (LISTEN needs a session)."""

    return psycopg.connect(
        str(database_url),
        autocommit=True,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
        application_name=LISTENER_APPLICATION_NAME,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )


class PostgresLiveEventListener:
    """Listens on `workshop_live_events` in a thread until stopped."""

    def __init__(
        self,
        connect: ListenerConnector,
        fanout: LiveEventFanout,
        first_delay_seconds: float = RECONNECT_FIRST_DELAY_SECONDS,
        max_delay_seconds: float = RECONNECT_MAX_DELAY_SECONDS,
    ) -> None:
        self._connect: ListenerConnector = connect
        self._fanout: LiveEventFanout = fanout
        self._first_delay_seconds: float = first_delay_seconds
        self._max_delay_seconds: float = max_delay_seconds
        self._stop_event: threading.Event = threading.Event()
        self._lock: threading.Lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._is_listening: threading.Event = threading.Event()

    def ensure_started(self) -> None:
        """Start the thread once (the first stream of the process)."""

        with self._lock:
            if self._thread is not None or self._stop_event.is_set():
                return

            self._thread = threading.Thread(
                target=self.run, name=LISTENER_THREAD_NAME, daemon=True
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
                    connection.execute(LISTEN_STATEMENT)
                    self._is_listening.set()
                    # Anything published before LISTEN (or while away) is lost.
                    self._fanout.resync_all()
                    delay_seconds = self._first_delay_seconds
                    self._receive(connection)
            except psycopg.Error as error:
                LOGGER.warning(
                    "Live event listener lost its database connection (%s); "
                    "retrying in %.1f s",
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
                self._handle(notification.payload)

            if time.monotonic() - last_probe >= PROBE_INTERVAL_SECONDS:
                connection.execute("select 1")
                last_probe = time.monotonic()

    def _handle(self, payload: str) -> None:
        try:
            event: LiveEvent = LiveEvent.model_validate_json(payload)
        except ValidationError:
            LOGGER.warning("Ignored a malformed live event notification")
            return

        self._fanout.dispatch(event)
