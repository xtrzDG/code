"""The whole application on Postgres: DATABASE_URL switches every collection."""

from psycopg import sql

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from tests.e2e.harness import E2E_ENVIRONMENT, start_workshop
from tests.e2e.journeys import BOOKING_REQUEST_RU, WIDGET_SESSION, open_restaurant
from tests.storage.postgres_server import ThrowawayPostgresServer


def count_rows(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    table_name: str,
) -> int:
    with postgres_server.admin_connection(database_name) as connection:
        row = connection.execute(
            sql.SQL("select count(*) from workshop.{}").format(
                sql.Identifier(table_name)
            )
        ).fetchone()

    assert row is not None
    return int(row[0])


def test_published_assistant_books_a_table_with_everything_in_postgres(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    database_url: DatabaseUrl,
) -> None:
    workshop = start_workshop({**E2E_ENVIRONMENT, "DATABASE_URL": str(database_url)})
    connection_pool = workshop.container.clients.postgres_pool()
    assert isinstance(connection_pool, PostgresConnectionPoolClient)

    with workshop.client as client:
        restaurant = open_restaurant(workshop)
        connected = client.put(
            f"{restaurant.base}/channels/web",
            json={},
            headers=restaurant.headers,
        )
        assert connected.status_code == 200, connected.text
        reply = client.post(
            f"/v1/widget/{restaurant.business_id}/messages",
            json={"session_key": WIDGET_SESSION, "text": BOOKING_REQUEST_RU},
        )
        assert reply.status_code == 200, reply.text
        # JSONB cannot store NUL; the message is still answered, not dropped.
        with_nul = client.post(
            f"/v1/widget/{restaurant.business_id}/messages",
            json={
                "session_key": WIDGET_SESSION,
                "text": "Спасибо\u0000!",
                "contact_name": "Нино\u0000",
            },
        )
        assert with_nul.status_code == 200, with_nul.text
        assert with_nul.json()["text"] is not None
        bookings = client.get(
            f"{restaurant.base}/bookings", headers=restaurant.headers
        ).json()["items"]
        tick = workshop.container.gateways.background_worker().run_once()

    assert [booking["time"] for booking in bookings] == ["19:00"]
    assert (tick.periodic_runs, tick.failures) == (7, 0)
    assert connection_pool.open_connection_count() == 0  # closed at shutdown
    stored: dict[str, int] = {
        str(definition.name): count_rows(
            postgres_server, database_name, str(definition.name)
        )
        for definition in DOCUMENT_COLLECTIONS
    }
    assert stored["users"] == 1
    assert stored["businesses"] == 1
    assert stored["business_profiles"] == 1
    assert stored["knowledge_items"] == 3
    assert stored["resources"] == 1
    assert stored["assistant_versions"] == 1
    assert stored["autotest_runs"] == 1
    # The real booking plus one sandbox booking per language from the
    # autotests the worker played (ka, ru, en).
    assert stored["bookings"] == 4
    assert stored["queued_jobs"] == 1
    assert stored["contacts"] >= 1
    assert stored["messages"] > 0
    assert stored["llm_turns"] > 0
    assert stored["audit_log_entries"] > 0
