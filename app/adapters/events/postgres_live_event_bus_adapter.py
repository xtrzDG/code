"""Live events between processes through Postgres NOTIFY / LISTEN."""

import psycopg

from app.adapters.events.live_event_fanout import LiveEventFanout
from app.adapters.events.postgres_live_event_listener import (
    LIVE_EVENTS_CHANNEL,
    PostgresLiveEventListener,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.live_events import (
    LiveEventBusAdapterContract,
    LiveEventSubscriberContract,
    LiveEventSubscriptionContract,
)
from app.schemas.dto.live_events import LiveEvent
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.live_events.constrained_strings import LiveEventId

NOTIFY_STATEMENT: str = "select pg_notify(%s, %s)"


class PostgresLiveEventBusAdapter(LiveEventBusAdapterContract):
    """
    `publish` is one `pg_notify` on a pooled connection (it works through a
    transaction pooler too); every API process that has an open stream
    keeps one LISTEN session (`PostgresLiveEventListener`, started with
    the first stream, so worker processes never hold one) and fans the
    events out to its streams. The payload is the event's JSON: kind, ids,
    business and time, never customer text, far below NOTIFY's 8000-byte
    limit.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        listener: PostgresLiveEventListener,
        fanout: LiveEventFanout,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._listener: PostgresLiveEventListener = listener
        self._fanout: LiveEventFanout = fanout

    def publish(self, event: LiveEvent) -> None:
        try:
            with self._connection_pool.connection() as connection:
                connection.execute(
                    NOTIFY_STATEMENT, (LIVE_EVENTS_CHANNEL, event.model_dump_json())
                )
        except psycopg.Error as error:
            raise ExternalServiceError(
                f"Could not publish a live event ({type(error).__name__})."
            ) from error

    def subscribe(
        self,
        business_id: BusinessId,
        subscriber: LiveEventSubscriberContract,
    ) -> LiveEventSubscriptionContract:
        subscription: LiveEventSubscriptionContract = self._fanout.subscribe(
            business_id, subscriber
        )
        self._listener.ensure_started()
        return subscription

    def replay_after(
        self,
        business_id: BusinessId,
        event_id: LiveEventId,
    ) -> list[LiveEvent] | None:
        return self._fanout.replay_after(business_id, event_id)

    def close(self) -> None:
        self._listener.stop()
        self._fanout.close()
