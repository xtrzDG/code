"""The whole application on Postgres: DATABASE_URL switches every collection."""

from psycopg import sql

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from tests.e2e.harness import start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import BOOKING_REQUEST_RU, WIDGET_SESSION, open_restaurant
from tests.e2e.widget_turns import ask_widget
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
        ask_widget(workshop, restaurant.business_id, WIDGET_SESSION, BOOKING_REQUEST_RU)
        # JSONB cannot store NUL; the message is still answered, not dropped.
        with_nul = ask_widget(
            workshop,
            restaurant.business_id,
            WIDGET_SESSION,
            "Спасибо\u0000!",
            contact_name="Нино\u0000",
        )
        assert with_nul["text"] is not None
        bookings = client.get(
            f"{restaurant.base}/bookings", headers=restaurant.headers
        ).json()["items"]
        tick = workshop.container.gateways.background_worker().run_once()

    assert [booking["time"] for booking in bookings] == ["19:00"]
    # The trace flush; the rest already ran this period (autotests tick).
    assert (tick.periodic_runs, tick.failures) == (1, 0)
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
    # The real booking plus two sandbox bookings per language from the
    # autotests the worker played (ka, ru, en): pass^k plays each booking
    # scenario twice.
    assert stored["bookings"] == 7
    # The autotest run, the safety job of each widget message (they find
    # their message answered), the staff notification of the booking and
    # the summary of the customer's conversation, due in two hours.
    assert stored["queued_jobs"] == 5
    assert stored["inbound_events"] == 2
    assert stored["outbound_messages"] == 1
    assert stored["contacts"] >= 1
    assert stored["messages"] > 0
    assert stored["llm_turns"] > 0
    assert stored["audit_log_entries"] > 0
