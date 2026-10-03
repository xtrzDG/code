"""
The one LISTEN connection of an API process: it hears every live event
published by any process (API instances, workers) and hands it to the
process's fan-out. It runs in a daemon thread
(`PostgresNotificationListener`: reconnects with growing pauses) and asks
every open stream to resync after a reconnect, because events published
while it was away are lost.
"""

import logging
from typing import LiteralString

from pydantic import ValidationError

from app.adapters.events.live_event_fanout import LiveEventFanout
from app.clients.postgres import postgres_notification_listener
from app.clients.postgres.postgres_notification_listener import (
    RECONNECT_FIRST_DELAY_SECONDS,
    RECONNECT_MAX_DELAY_SECONDS,
    ListenerConnection,
    ListenerConnector,
    PostgresNotificationListener,
)
from app.schemas.dto.live_events import LiveEvent
from app.schemas.typings.platform.strings import DatabaseUrl

LOGGER: logging.Logger = logging.getLogger(__name__)

LIVE_EVENTS_CHANNEL: LiteralString = "workshop_live_events"
LISTENER_APPLICATION_NAME: str = "assistant-workshop-live-events"
LISTENER_THREAD_NAME: str = "live-event-listener"


def connect_listener(database_url: DatabaseUrl) -> ListenerConnection:
    """The live events' own LISTEN session (named in pg_stat_activity)."""

    return postgres_notification_listener.connect_listener(
        database_url, LISTENER_APPLICATION_NAME
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
        self._fanout: LiveEventFanout = fanout
        self._listener: PostgresNotificationListener = PostgresNotificationListener(
            connect=connect,
            channel=LIVE_EVENTS_CHANNEL,
            on_notification=self._handle,
            # Anything published before LISTEN (or while away) is lost.
            on_listening=fanout.resync_all,
            thread_name=LISTENER_THREAD_NAME,
            first_delay_seconds=first_delay_seconds,
            max_delay_seconds=max_delay_seconds,
        )

    def ensure_started(self) -> None:
        """Start the thread once (the first stream of the process)."""

        self._listener.ensure_started()

    def wait_until_listening(self, timeout_seconds: float) -> bool:
        """True once LISTEN is in place (tests and startup checks)."""

        return self._listener.wait_until_listening(timeout_seconds)

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._listener.stop(timeout_seconds)

    def run(self) -> None:
        """Listen in the calling thread until stopped (tests)."""

        self._listener.run()

    def _handle(self, payload: str) -> None:
        try:
            event: LiveEvent = LiveEvent.model_validate_json(payload)
        except ValidationError:
            LOGGER.warning("Ignored a malformed live event notification")
            return

        self._fanout.dispatch(event)
